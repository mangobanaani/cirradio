SUMMARY = "IMA/EVM measurement and appraisal policy for CIRRADIO"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://ima-policy.conf"

do_install() {
    install -d ${D}${sysconfdir}/ima
    install -m 0644 ${WORKDIR}/ima-policy.conf ${D}${sysconfdir}/ima/ima-policy
}

FILES_${PN} = "${sysconfdir}/ima/*"

RDEPENDS_${PN} = "ima-evm-utils"
