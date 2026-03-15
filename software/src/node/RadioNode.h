#pragma once
#include "hal/SimChannel.h"
#include "hal/SimRadioHal.h"
#include "hal/Types.h"
#include "security/SoftHsm.h"
#include "security/KeyManager.h"
#include "fhss/HopSequencer.h"
#include "tdma/SlotScheduler.h"
#include "network/MeshRouter.h"
#include "network/PeerDiscovery.h"
#include "network/NetJoin.h"
#include "voice/VoiceCodec.h"
#include "voice/JitterBuffer.h"
#include "voice/SimAudioHal.h"
#include "mgmt/CLIShell.h"

#include <memory>
#include <vector>
#include <optional>
#include <cstdint>

namespace cirradio::node {

enum class NodeState : uint8_t {
    Idle,
    Listening,
    Active
};

// Wire-format message header for data exchange between nodes
struct MessageHeader {
    uint8_t msg_type;       // 0 = beacon, 1 = data, 2 = voice
    uint32_t src_node;
    uint32_t dst_node;
    uint32_t payload_len;
};

struct ReceivedData {
    uint32_t source;
    std::vector<uint8_t> payload;
};

struct ReceivedVoice {
    uint32_t source;
    std::vector<int16_t> audio;
};

class RadioNode {
public:
    RadioNode(uint32_t id, std::shared_ptr<hal::SimChannel> channel);
    ~RadioNode();

    // State management
    NodeState state() const;
    void start();

    // Frame processing
    void tick();

    // Peer discovery
    std::vector<uint32_t> peers() const;

    // Data exchange
    void send_data(uint32_t dest, const std::vector<uint8_t>& payload);
    std::optional<ReceivedData> receive_data();

    // Voice exchange
    void voice_tx(uint32_t dest, const std::vector<int16_t>& audio);
    std::optional<ReceivedVoice> voice_rx();

    // Key provisioning
    void provision_keys(const std::vector<uint8_t>& tek,
                        const std::vector<uint8_t>& fhek);

    // CLI delegation
    mgmt::CommandResult cli_execute(const std::string& cmd);

    // Position for range-limited simulation
    void set_position(double meters);

    uint32_t id() const { return id_; }

private:
    static constexpr uint8_t kMsgTypeBeacon = 0;
    static constexpr uint8_t kMsgTypeData   = 1;
    static constexpr uint8_t kMsgTypeVoice  = 2;

    // Band parameters (UHF 225-512 MHz, 25 kHz spacing)
    static constexpr hal::Frequency kMinFreq = 225000000;
    static constexpr hal::Frequency kMaxFreq = 512000000;
    static constexpr hal::Frequency kChannelSpacing = 25000;
    // Discovery rendezvous frequency
    static constexpr hal::Frequency kDiscoveryFreq = 300000000;

    uint32_t id_;
    NodeState state_ = NodeState::Idle;
    uint32_t frame_number_ = 0;
    double position_meters_ = 0.0;

    // Pre-provisioned keys (set before start())
    std::vector<uint8_t> provisioned_tek_;
    std::vector<uint8_t> provisioned_fhek_;
    bool keys_provisioned_ = false;

    // Subsystems (owned)
    std::shared_ptr<hal::SimChannel> channel_;
    std::unique_ptr<hal::SimRadioHal> radio_;
    std::unique_ptr<security::SoftHsm> hsm_;
    std::unique_ptr<security::KeyManager> key_mgr_;
    std::unique_ptr<fhss::HopSequencer> hop_seq_;
    std::unique_ptr<tdma::SlotScheduler> scheduler_;
    std::unique_ptr<network::MeshRouter> router_;
    std::unique_ptr<network::PeerDiscovery> discovery_;
    std::unique_ptr<network::NetJoin> net_join_;
    std::unique_ptr<voice::VoiceCodec> voice_codec_;
    std::unique_ptr<voice::JitterBuffer> jitter_buf_;
    std::unique_ptr<voice::SimAudioHal> audio_hal_;
    std::unique_ptr<mgmt::CLIShell> cli_;

    // EC identity keys (DER-encoded)
    std::vector<uint8_t> identity_private_key_;
    std::vector<uint8_t> identity_public_key_;

    // Receive buffers
    std::vector<ReceivedData> data_inbox_;
    std::vector<ReceivedVoice> voice_inbox_;

    // Internal helpers
    void generate_identity_keys();
    void transmit_on_channel(hal::Frequency freq,
                             const std::vector<uint8_t>& payload);
    std::vector<uint8_t> receive_from_channel(hal::Frequency freq);

    // Serialization
    std::vector<uint8_t> serialize_header(const MessageHeader& hdr) const;
    std::optional<MessageHeader> deserialize_header(
        const std::vector<uint8_t>& data) const;
};

}  // namespace cirradio::node
