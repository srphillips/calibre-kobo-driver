# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai

"""KePub metadata writer."""

__license__ = "GPL v3"
__copyright__ = "2015, David Forrester <davidfor@internode.on.net>"
__docformat__ = "markdown en"

import os
from cStringIO import StringIO

from calibre.customize.builtins import EPUBMetadataWriter
from calibre.ebooks.metadata.epub import get_zip_reader
from calibre.ebooks.metadata.opf2 import OPF
from calibre.utils.localunzip import LocalZipFile
from calibre.utils.logging import default_log
from calibre.utils.zipfile import safe_replace

from calibre_plugins.kepubmdwriter.common import plugin_minimum_calibre_version
from calibre_plugins.kepubmdwriter.common import plugin_version

# Support load_translations() without forcing calibre 1.9+
try:
    load_translations()
except NameError:
    pass


class KEPUBMetadataWriter(EPUBMetadataWriter):
    """Setting KePub metadata.

    KePub metadata is almost identical to ePub. The sole difference is when
    writing out metadata, KePub files are stricter about how to identify the
    cover image.
    """

    name = "KePub Metadata Writer"
    author = "David Forrester"
    description = _("Set metadata in %s files") % "Kobo ePub"  # noqa: F821
    file_types = set(["kepub"])
    version = plugin_version
    minimum_calibre_version = plugin_minimum_calibre_version

    # The logic in here to detect a cover image is mostly duplicated from
    # modify_epub() in common.py. Updates to the logic here probably need an
    # accompanying update there.
    def set_metadata(self, stream, mi, type):
        """Set standard ePub metadata then properly set the cover image."""
        default_log(
            "KEPUBMetadataWriter::set_metadata - self.__class__={0}".format(
                self.__class__
            )
        )
        super(KEPUBMetadataWriter, self).set_metadata(stream, mi, type)

        stream.seek(0)
        reader = get_zip_reader(stream, root=os.getcwdu())

        found_cover = False
        covers = reader.opf.raster_cover_path(reader.opf.metadata)
        if len(covers) > 0:
            default_log("KEPUBMetadataWriter::set_metadata - covers={0}".format(covers))
            cover_id = covers[0].get("content")
            default_log(
                "KEPUBMetadataWriter::set_metadata - cover_id={0}".format(cover_id)
            )
            for item in reader.opf.itermanifest():
                if item.get("id", None) == cover_id:
                    mt = item.get("media-type", "")
                    if mt and mt.startswith("image/"):
                        default_log("KEPUBMetadataWriter::set_metadata - found cover")
                        item.set("properties", "cover-image")
                        found_cover = True
                        break
            if not found_cover:
                default_log(
                    "KEPUBMetadataWriter::set_metadata - looking for cover "
                    "using href"
                )
                for item in reader.opf.itermanifest():
                    if item.get("href", None) == cover_id:
                        mt = item.get("media-type", "")
                        if mt and mt.startswith("image/"):
                            default_log(
                                "KEPUBMetadataWriter::set_metadata -found " "cover"
                            )
                            item.set("properties", "cover-image")
                            found_cover = True

            if found_cover:
                newopf = StringIO(reader.opf.render())
                if isinstance(reader.archive, LocalZipFile):
                    reader.archive.safe_replace(reader.container[OPF.MIMETYPE], newopf)
                else:
                    safe_replace(stream, reader.container[OPF.MIMETYPE], newopf)
