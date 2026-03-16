#include "node/RadioNode.h"
#include <spdlog/spdlog.h>
#include <openssl/evp.h>
#include <openssl/ec.h>
#include <openssl/x509.h>
#include <cstring>
#include <cmath>
#include <complex>

namespace cirradio::node {

namespace {

// Encode a uint32_t into 4 bytes (big-endian)
void encode_u32(uint8_t* buf, uint32_t val) {
    buf[0] = static_cast<uint8_t>((val >> 24) & 0xFF);
    buf[1] = static_cast<uint8_t>((val >> 16) & 0xFF);
    buf[2] = static_cast<uint8_t>((val >>  8) & 0xFF);
    buf[3] = static_cast<uint8_t>( val        & 0xFF);
}

uint32_t decode_u32(const uint8_t* buf) {
    return (static_cast<uint32_t>(buf[0]) << 24) |
           (static_cast<uint32_t>(buf[1]) << 16) |
           (static_cast<uint32_t>(buf[2]) <<  8) |
            static_cast<uint32_t>(buf[3]);
}

// Convert byte payload to complex samples for SimChannel transport
std::vector<hal::Sample> bytes_to_samples(const std::vector<uint8_t>& data) {
    std::vector<hal::Sample> samples;
    samples.reserve(data.size());
    for (uint8_t b : data) {
        samples.emplace_back(static_cast<float>(b), 0.0f);
    }
    return samples;
}

// Convert complex samples back to byte payload
std::vector<uint8_t> samples_to_bytes(const std::vector<hal::Sample>& samples) {
    std::vector<uint8_t> data;
    data.reserve(samples.size());
    for (const auto& s : samples) {
        int val = static_cast<int>(std::lround(s.real()));
        data.push_back(static_cast<uint8_t>(std::clamp(val, 0, 255)));
    }
    return data;
}

}  // namespace

RadioNode::RadioNode(uint32_t id, std::shared_ptr<hal::SimChannel> channel)
    : id_(id)
    , channel_(std::move(channel))
    , emcon_mgr_(null_axi_, transec_cfg_) {
    // Create subsystems that don't depend on keys
    radio_ = std::make_unique<hal::SimRadioHal>(channel_);
    hsm_ = std::make_unique<security::SoftHsm>();
    key_mgr_ = std::make_unique<security::KeyManager>(*hsm_);
    scheduler_ = std::make_unique<tdma::SlotScheduler>(id);
    router_ = std::make_unique<network::MeshRouter>(id);
    discovery_ = std::make_unique<network::PeerDiscovery>(id);
    voice_codec_ = std::make_unique<voice::VoiceCodec>();
    jitter_buf_ = std::make_unique<voice::JitterBuffer>();
    audio_hal_ = std::make_unique<voice::SimAudioHal>();
    cli_ = std::make_unique<mgmt::CLIShell>();

    // Wire EmconManager and TransecConfig into CLIShell
    cli_->set_emcon_manager(&emcon_mgr_);
    cli_->set_transec_config(&transec_cfg_);

    // Generate EC P-384 identity key pair for NetJoin
    generate_identity_keys();

    // Create SecurityManager
    security_mgr_ = std::make_unique<security::SecurityManager>(
        *key_mgr_, *hsm_, null_axi_, ik_handle_);

    // Wire EmconManager into TamperMonitor callback via post-zeroize hook
    security_mgr_->set_post_zeroize_hook([this]() {
        emcon_mgr_.force_emcon0();
    });

    // Create NetJoin with identity keys
    net_join_ = std::make_unique<network::NetJoin>(
        id, identity_private_key_, identity_public_key_);

    spdlog::debug("RadioNode {} created", id_);
}

RadioNode::~RadioNode() = default;

NodeState RadioNode::state() const {
    return state_;
}

void RadioNode::start() {
    if (state_ != NodeState::Idle) {
        return;
    }

    // Initialize keys
    if (keys_provisioned_) {
        key_mgr_->initialize_kek();
        key_mgr_->set_tek_raw(provisioned_tek_);
        key_mgr_->set_fhek_raw(provisioned_fhek_);
    } else {
        if (!key_mgr_->is_initialized()) {
            key_mgr_->initialize_kek();
            key_mgr_->generate_tek();
            key_mgr_->generate_fhek();
        }
    }

    // Create HopSequencer with the FHEK
    auto fhek = key_mgr_->export_fhek_for_fpga();
    hop_seq_ = std::make_unique<fhss::HopSequencer>(
        std::span<const uint8_t>(fhek), kMinFreq, kMaxFreq, kChannelSpacing);

    // Enable radio TX
    radio_->set_tx_enabled(true);
    radio_->configure({kDiscoveryFreq, 48000, 25000, 10.0f});

    // Claim slot 1 for this node
    scheduler_->claim_slot(static_cast<uint8_t>(1 + ((id_ - 1) % 14)));

    state_ = NodeState::Listening;
    spdlog::debug("RadioNode {} started, state=Listening", id_);
}

void RadioNode::tick() {
    if (state_ == NodeState::Idle) {
        return;
    }

    // 1. Generate and transmit a discovery beacon on the rendezvous frequency
    auto beacon = discovery_->generate_beacon(
        static_cast<uint8_t>(discovery_->discovered_nodes().size() + 1));

    // Serialize beacon into a simple wire format
    // msg_type=0 (beacon), src=node_id, dst=0 (broadcast), payload=beacon fields
    std::vector<uint8_t> beacon_payload;
    beacon_payload.resize(9);
    encode_u32(beacon_payload.data(), beacon.node_id);
    encode_u32(beacon_payload.data() + 4, beacon.net_id);
    beacon_payload[8] = beacon.num_nodes;

    MessageHeader hdr{};
    hdr.msg_type = kMsgTypeBeacon;
    hdr.src_node = id_;
    hdr.dst_node = 0;  // broadcast
    hdr.payload_len = static_cast<uint32_t>(beacon_payload.size());

    auto wire = serialize_header(hdr);
    wire.insert(wire.end(), beacon_payload.begin(), beacon_payload.end());

    transmit_on_channel(kDiscoveryFreq, wire);

    // 2. Receive any beacons on the discovery frequency
    auto rx_data = receive_from_channel(kDiscoveryFreq);
    if (!rx_data.empty()) {
        // Parse all messages from received data
        size_t offset = 0;
        while (offset + 13 <= rx_data.size()) {
            // Try to parse a header at this offset
            std::vector<uint8_t> hdr_data(rx_data.begin() + static_cast<std::ptrdiff_t>(offset),
                                          rx_data.begin() + static_cast<std::ptrdiff_t>(offset) + 13);
            auto parsed_hdr = deserialize_header(hdr_data);
            if (!parsed_hdr) {
                break;
            }

            size_t msg_end = offset + 13 + parsed_hdr->payload_len;
            if (msg_end > rx_data.size()) {
                break;
            }

            if (parsed_hdr->msg_type == kMsgTypeBeacon &&
                parsed_hdr->payload_len >= 9) {
                const uint8_t* p = rx_data.data() + offset + 13;
                network::DiscoveryBeacon rx_beacon;
                rx_beacon.node_id = decode_u32(p);
                rx_beacon.net_id = decode_u32(p + 4);
                rx_beacon.num_nodes = p[8];
                rx_beacon.timestamp = std::chrono::steady_clock::now();

                if (discovery_->process_beacon(rx_beacon)) {
                    router_->update_neighbor(rx_beacon.node_id, 1.0f);
                    spdlog::debug("RadioNode {} discovered peer {}",
                                  id_, rx_beacon.node_id);
                }
            } else if (parsed_hdr->msg_type == kMsgTypeData) {
                // Data message - check if it's for us
                if (parsed_hdr->dst_node == id_ || parsed_hdr->dst_node == 0) {
                    std::vector<uint8_t> payload(
                        rx_data.begin() + static_cast<std::ptrdiff_t>(offset + 13),
                        rx_data.begin() + static_cast<std::ptrdiff_t>(msg_end));

                    // Decrypt if we have a TEK
                    if (key_mgr_->is_initialized()) {
                        auto decrypted = key_mgr_->decrypt_with_tek(payload);
                        if (decrypted) {
                            data_inbox_.push_back(
                                ReceivedData{parsed_hdr->src_node, *decrypted});
                        }
                    }
                }
            } else if (parsed_hdr->msg_type == kMsgTypeVoice) {
                if (parsed_hdr->dst_node == id_ || parsed_hdr->dst_node == 0) {
                    std::vector<uint8_t> payload(
                        rx_data.begin() + static_cast<std::ptrdiff_t>(offset + 13),
                        rx_data.begin() + static_cast<std::ptrdiff_t>(msg_end));

                    if (key_mgr_->is_initialized()) {
                        auto decrypted = key_mgr_->decrypt_with_tek(payload);
                        if (decrypted) {
                            // Decode voice
                            auto audio = voice_codec_->decode(*decrypted);
                            voice_inbox_.push_back(
                                ReceivedVoice{parsed_hdr->src_node, audio});
                        }
                    }
                }
            }

            offset = msg_end;
        }
    }

    // 3. Also check for data/voice on the current hop frequency
    if (hop_seq_) {
        auto hop_freq = hop_seq_->get_hop_frequency(0, frame_number_);
        auto hop_data = receive_from_channel(hop_freq);
        if (!hop_data.empty()) {
            size_t offset = 0;
            while (offset + 13 <= hop_data.size()) {
                std::vector<uint8_t> hdr_data(
                    hop_data.begin() + static_cast<std::ptrdiff_t>(offset),
                    hop_data.begin() + static_cast<std::ptrdiff_t>(offset) + 13);
                auto parsed_hdr = deserialize_header(hdr_data);
                if (!parsed_hdr) break;

                size_t msg_end = offset + 13 + parsed_hdr->payload_len;
                if (msg_end > hop_data.size()) break;

                if (parsed_hdr->msg_type == kMsgTypeData &&
                    (parsed_hdr->dst_node == id_ || parsed_hdr->dst_node == 0)) {
                    std::vector<uint8_t> payload(
                        hop_data.begin() + static_cast<std::ptrdiff_t>(offset + 13),
                        hop_data.begin() + static_cast<std::ptrdiff_t>(msg_end));
                    if (key_mgr_->is_initialized()) {
                        auto decrypted = key_mgr_->decrypt_with_tek(payload);
                        if (decrypted) {
                            data_inbox_.push_back(
                                ReceivedData{parsed_hdr->src_node, *decrypted});
                        }
                    }
                } else if (parsed_hdr->msg_type == kMsgTypeVoice &&
                           (parsed_hdr->dst_node == id_ || parsed_hdr->dst_node == 0)) {
                    std::vector<uint8_t> payload(
                        hop_data.begin() + static_cast<std::ptrdiff_t>(offset + 13),
                        hop_data.begin() + static_cast<std::ptrdiff_t>(msg_end));
                    if (key_mgr_->is_initialized()) {
                        auto decrypted = key_mgr_->decrypt_with_tek(payload);
                        if (decrypted) {
                            auto audio = voice_codec_->decode(*decrypted);
                            voice_inbox_.push_back(
                                ReceivedVoice{parsed_hdr->src_node, audio});
                        }
                    }
                }

                offset = msg_end;
            }
        }
    }

    // 4. Advance TDMA frame
    scheduler_->advance_frame();
    frame_number_++;
}

std::vector<uint32_t> RadioNode::peers() const {
    return discovery_->discovered_nodes();
}

void RadioNode::send_data(uint32_t dest, const std::vector<uint8_t>& payload) {
    if (state_ == NodeState::Idle || !key_mgr_->is_initialized()) {
        return;
    }

    // Encrypt payload with TEK
    auto encrypted = key_mgr_->encrypt_with_tek(payload);
    if (!encrypted) {
        return;
    }

    MessageHeader hdr{};
    hdr.msg_type = kMsgTypeData;
    hdr.src_node = id_;
    hdr.dst_node = dest;
    hdr.payload_len = static_cast<uint32_t>(encrypted->size());

    auto wire = serialize_header(hdr);
    wire.insert(wire.end(), encrypted->begin(), encrypted->end());

    // Transmit on current hop frequency
    if (hop_seq_) {
        auto freq = hop_seq_->get_hop_frequency(0, frame_number_);
        transmit_on_channel(freq, wire);
    }
}

std::optional<ReceivedData> RadioNode::receive_data() {
    if (data_inbox_.empty()) {
        return std::nullopt;
    }
    auto front = std::move(data_inbox_.front());
    data_inbox_.erase(data_inbox_.begin());
    return front;
}

void RadioNode::voice_tx(uint32_t dest, const std::vector<int16_t>& audio) {
    if (state_ == NodeState::Idle || !key_mgr_->is_initialized()) {
        return;
    }

    // Encode audio with voice codec
    auto encoded = voice_codec_->encode(audio);

    // Encrypt with TEK
    auto encrypted = key_mgr_->encrypt_with_tek(encoded);
    if (!encrypted) {
        return;
    }

    MessageHeader hdr{};
    hdr.msg_type = kMsgTypeVoice;
    hdr.src_node = id_;
    hdr.dst_node = dest;
    hdr.payload_len = static_cast<uint32_t>(encrypted->size());

    auto wire = serialize_header(hdr);
    wire.insert(wire.end(), encrypted->begin(), encrypted->end());

    // Transmit on current hop frequency
    if (hop_seq_) {
        auto freq = hop_seq_->get_hop_frequency(0, frame_number_);
        transmit_on_channel(freq, wire);
    }
}

std::optional<ReceivedVoice> RadioNode::voice_rx() {
    if (voice_inbox_.empty()) {
        return std::nullopt;
    }
    auto front = std::move(voice_inbox_.front());
    voice_inbox_.erase(voice_inbox_.begin());
    return front;
}

void RadioNode::provision_keys(const std::vector<uint8_t>& tek,
                               const std::vector<uint8_t>& fhek) {
    provisioned_tek_ = tek;
    provisioned_fhek_ = fhek;
    keys_provisioned_ = true;
}

mgmt::CommandResult RadioNode::cli_execute(const std::string& cmd) {
    return cli_->execute(cmd);
}

void RadioNode::set_position(double meters) {
    position_meters_ = meters;
}

void RadioNode::generate_identity_keys() {
    EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, nullptr);
    if (!ctx) {
        spdlog::error("RadioNode {}: failed to create EVP_PKEY_CTX", id_);
        return;
    }

    EVP_PKEY* pkey = nullptr;
    bool ok = (EVP_PKEY_keygen_init(ctx) == 1) &&
              (EVP_PKEY_CTX_set_ec_paramgen_curve_nid(ctx, NID_secp384r1) == 1) &&
              (EVP_PKEY_keygen(ctx, &pkey) == 1);
    EVP_PKEY_CTX_free(ctx);

    if (!ok || !pkey) {
        spdlog::error("RadioNode {}: failed to generate EC key pair", id_);
        return;
    }

    // Serialize private key to DER
    int priv_len = i2d_PrivateKey(pkey, nullptr);
    if (priv_len > 0) {
        identity_private_key_.resize(static_cast<size_t>(priv_len));
        unsigned char* p = identity_private_key_.data();
        i2d_PrivateKey(pkey, &p);
    }

    // Serialize public key to DER
    int pub_len = i2d_PUBKEY(pkey, nullptr);
    if (pub_len > 0) {
        identity_public_key_.resize(static_cast<size_t>(pub_len));
        unsigned char* p = identity_public_key_.data();
        i2d_PUBKEY(pkey, &p);
    }

    EVP_PKEY_free(pkey);

    // Import private key into HSM for SecurityManager
    if (!identity_private_key_.empty()) {
        ik_handle_ = hsm_->import_ec_key_der(identity_private_key_);
    }
}

void RadioNode::transmit_on_channel(hal::Frequency freq,
                                    const std::vector<uint8_t>& payload) {
    radio_->tune(freq);
    auto samples = bytes_to_samples(payload);
    hal::ConstSampleBuffer buf(samples);
    radio_->transmit(buf);
}

std::vector<uint8_t> RadioNode::receive_from_channel(hal::Frequency freq) {
    radio_->tune(freq);
    std::vector<hal::Sample> buffer(4096);
    size_t n = radio_->receive(std::span<hal::Sample>(buffer));
    if (n == 0) {
        return {};
    }
    buffer.resize(n);
    return samples_to_bytes(buffer);
}

std::vector<uint8_t> RadioNode::serialize_header(const MessageHeader& hdr) const {
    // 1 byte msg_type + 4 bytes src + 4 bytes dst + 4 bytes payload_len = 13
    std::vector<uint8_t> data(13);
    data[0] = hdr.msg_type;
    encode_u32(data.data() + 1, hdr.src_node);
    encode_u32(data.data() + 5, hdr.dst_node);
    encode_u32(data.data() + 9, hdr.payload_len);
    return data;
}

std::optional<MessageHeader> RadioNode::deserialize_header(
    const std::vector<uint8_t>& data) const {
    if (data.size() < 13) {
        return std::nullopt;
    }
    MessageHeader hdr;
    hdr.msg_type = data[0];
    hdr.src_node = decode_u32(data.data() + 1);
    hdr.dst_node = decode_u32(data.data() + 5);
    hdr.payload_len = decode_u32(data.data() + 9);
    return hdr;
}

}  // namespace cirradio::node
