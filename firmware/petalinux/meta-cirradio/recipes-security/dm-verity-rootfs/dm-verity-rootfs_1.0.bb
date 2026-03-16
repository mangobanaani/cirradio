SUMMARY = "Post-processing task: generate dm-verity hash tree for cirradio rootfs"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

# Runs after rootfs image build to produce:
#   cirradio-rootfs.squashfs        (read-only root)
#   cirradio-rootfs.squashfs.verity (dm-verity hash tree)
#   root_hash.txt                   (hash for U-Boot command line, baked in at signing)

DEPENDS = "squashfs-tools cryptsetup"

do_generate_verity_image() {
    mksquashfs ${IMAGE_ROOTFS} ${DEPLOY_DIR_IMAGE}/${IMAGE_NAME}.squashfs \
        -noappend -comp xz -b 131072

    veritysetup format \
        ${DEPLOY_DIR_IMAGE}/${IMAGE_NAME}.squashfs \
        ${DEPLOY_DIR_IMAGE}/${IMAGE_NAME}.squashfs.verity \
        | tee ${DEPLOY_DIR_IMAGE}/root_hash.txt
}

addtask generate_verity_image after do_rootfs before do_image_complete
