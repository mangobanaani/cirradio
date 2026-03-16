SUMMARY = "seccomp allowlist profile for cirradio daemon"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://cirradio.seccomp"

do_install() {
    install -d ${D}${sysconfdir}/cirradio
    install -m 0644 ${WORKDIR}/cirradio.seccomp \
        ${D}${sysconfdir}/cirradio/cirradio.seccomp
}

FILES_${PN} = "${sysconfdir}/cirradio/*"
