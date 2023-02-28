# ---LICENSE-BEGIN - DO NOT CHANGE OR MOVE THIS HEADER
# This file is part of the Neurorobotics Platform software
# Copyright (C) 2014,2015,2016,2017,2018,2019,2020,2021 Human Brain Project
# https://www.humanbrainproject.eu
#
# The Human Brain Project is a European Commission funded project
# in the frame of the Horizon2020 FET Flagship plan.
# http://ec.europa.eu/programmes/horizon2020/en/h2020-section/fet-flagships
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
# ---LICENSE-END
# This is the default sphinx configuration file, that is to be included 
# in corresponding conf.py files of each project

import sys, os
from unittest import mock

# -- General configuration -----------------------------------------------------
# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.viewcode',
              'sphinxcontrib.apidoc',
              'sphinxcontrib.images',
              'sphinx.ext.coverage',
              'sphinx.ext.autosummary',
              'sphinx.ext.todo']

# This parameters should be defined in individual conf.py
# i.e.:
# apidoc_module_dir = '../../hbp_nrp_backend'
apidoc_output_dir = 'apidoc'
apidoc_excluded_paths = ['*tests/*', 'version.py']
apidoc_toc_file = False
apidoc_separate_modules = True
apidoc_module_first = True
add_module_names = False

# Make thumbnails behavior from the images
images_config = {
    "override_image_directive": True
}

todo_include_todos = True
todo_emit_warnings = True

numfig = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
# This parameters should be defined in individual conf.py
# i.e.:
# project = u'NRP Backend'
copyright = u'2023, Human Brain Project'

# This values are to be overwritten by projects
version = "undefined"
release = "undefined"


# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build', '_templates']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- Options for HTML output ---------------------------------------------------
# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
