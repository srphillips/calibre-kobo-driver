# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai

"""Output processing for KePub files."""

__license__ = "GPL v3"
__copyright__ = "2013, Joel Goguen <jgoguen@jgoguen.ca>"
__docformat__ = "markdown en"

import json
import os
from datetime import datetime

from calibre.constants import config_dir
from calibre.customize.conversion import OptionRecommendation
from calibre.customize.conversion import OutputFormatPlugin
from calibre.ebooks.conversion.plugins.epub_output import EPUBOutput
from calibre.ebooks.metadata.book.base import Metadata
from calibre.ebooks.metadata.book.base import NULL_VALUES
from calibre.utils.logging import default_log

from calibre_plugins.kepubout.common import modify_epub
from calibre_plugins.kepubout.common import plugin_minimum_calibre_version
from calibre_plugins.kepubout.common import plugin_version
from calibre_plugins.kepubout.container import KEPubContainer

# Support load_translations() without forcing calibre 1.9+
try:
    load_translations()
except NameError:
    pass


class KEPubOutput(OutputFormatPlugin):
    """Allows calibre to convert any known source format to a KePub file."""

    name = "KePub Output"
    author = "Joel Goguen"
    file_type = "kepub"
    version = plugin_version
    minimum_calibre_version = plugin_minimum_calibre_version

    epub_output_plugin = None
    configdir = os.path.join(config_dir, "plugins")
    reference_kepub = os.path.join(configdir, "reference.kepub.epub")
    options = set(
        [
            OptionRecommendation(
                name="kepub_hyphenate",
                recommended_value=True,
                help=" ".join(
                    [
                        _(  # noqa: F821
                            "Select this to add a CSS file which enables hyphenation."
                        ),
                        _(  # noqa: F821
                            "The language used will be the language defined for the "
                            "book in calibre."
                        ),
                        _(  # noqa: F821
                            "Please see the README file for directions on updating "
                            "hyphenation dictionaries."
                        ),
                    ]
                ),
            ),
            OptionRecommendation(
                name="kepub_disable_hyphenation",
                recommended_value=False,
                help=" ".join(
                    [
                        _(  # noqa: F821
                            "Select this to disable all hyphenation in a book."
                        ),
                        _(  # noqa: F821
                            "This takes precedence over the hyphenation option."
                        ),
                    ]
                ),
            ),
            OptionRecommendation(
                name="kepub_clean_markup",
                recommended_value=True,
                help=_(  # noqa: F821
                    "Select this to clean up the internal ePub markup."
                ),
            ),
        ]
    )
    recommendations = set([])

    def __init__(self, *args, **kwargs):
        """Initialize the KePub output converter."""
        self.epub_output_plugin = EPUBOutput(*args, **kwargs)
        self.options = self.options.union(self.epub_output_plugin.options)
        self.recommendations = self.recommendations.union(
            self.epub_output_plugin.recommendations
        )
        OutputFormatPlugin.__init__(self, *args, **kwargs)

    def gui_configuration_widget(
        self, parent, get_option_by_name, get_option_help, db, book_id=None
    ):
        """Set up the plugin configuration widget."""
        from calibre_plugins.kepubout.conversion.output_config import PluginWidget

        return PluginWidget(parent, get_option_by_name, get_option_help, db, book_id)

    def convert(self, oeb_book, output, input_plugin, opts, log):
        """Convert from calibre's internal format to KePub."""
        self.epub_output_plugin.convert(oeb_book, output, input_plugin, opts, log)
        container = KEPubContainer(output, default_log)

        if container.is_drm_encumbered:
            return

        # Write the details file
        o = {
            "kepub_output_version": ".".join([str(n) for n in self.version]),
            "kepub_output_currenttime": datetime.utcnow().ctime(),
        }
        kte_data_file = self.temporary_file("_KePubOutputPluginInfo")
        kte_data_file.write(json.dumps(o))
        kte_data_file.close()
        container.copy_file_to_container(
            kte_data_file.name, name="plugininfo.kte", mt="application/json"
        )

        title = container.opf_xpath("./opf:metadata/dc:title/text()")
        if len(title) > 0:
            title = title[0]
        else:
            title = NULL_VALUES["title"]
        authors = container.opf_xpath(
            './opf:metadata/dc:creator[@opf:role="aut"]/text()'
        )
        if len(authors) < 1:
            authors = NULL_VALUES["authors"]
        mi = Metadata(title, authors)
        language = container.opf_xpath("./opf:metadata/dc:language/text()")
        if len(language) > 0:
            mi.languages = language
            language = language[0]
        else:
            mi.languages = NULL_VALUES["languages"]
            language = NULL_VALUES["language"]
        mi.language

        modify_epub(
            container,
            output,
            metadata=mi,
            opts={
                "clean_markup": opts.kepub_clean_markup,
                "hyphenate": opts.kepub_hyphenate,
                "no-hyphens": opts.kepub_disable_hyphenation,
                "smarten_punctuation": False,
                "extended_kepub_features": True,
            },
        )
