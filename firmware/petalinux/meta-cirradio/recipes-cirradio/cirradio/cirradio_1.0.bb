SUMMARY = "CIRRADIO embedded application"
LICENSE = "CLOSED"

SRC_URI = "file://${TOPDIR}/../../../software/embedded"
S = "${WORKDIR}/embedded"

DEPENDS = "libiio gpsd codec2"

inherit cmake systemd

SYSTEMD_SERVICE_${PN} = "cirradio.service"

do_configure() {
    cmake ${S} \
        -DCMAKE_TOOLCHAIN_FILE=${STAGING_DATADIR}/cmake/OEToolchainConfig.cmake \
        -DCMAKE_BUILD_TYPE=Release \
        ${@cmake_extra_oecmake}
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${B}/cirradio_app ${D}${bindir}/cirradio

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/cirradio.service ${D}${systemd_system_unitdir}/

    install -d ${D}/lib/firmware
}
