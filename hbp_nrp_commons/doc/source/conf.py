# ---LICENSE-BEGIN - DO NOT CHANGE OR MOVE THIS HEADER
# This file is part of the Neurorobotics Platform software
# Copyright (C) 2014,2015,2016,2017 Human Brain Project
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
# -*- coding: utf-8 -*-

import sys, os
nrp_backend_root = os.path.join(os.environ["HBP"], "nrp-backend")
# import conf.py from nrp-backend/.ci
sys.path.insert(0, os.path.join(nrp_backend_root, ".ci", "python", "doc"))

from sphinxconf import *

# import modules needed by this project
sys.path.insert(0, os.path.join(nrp_backend_root, 'hbp_nrp_commons'))  # Source code dir relative to this file
import hbp_nrp_commons

# -- General configuration -----------------------------------------------------
# extend or overwrite extentions from common config
# extensions.append('smth')
apidoc_module_dir = '../../hbp_nrp_commons'

# General information about the project.
project = u'NRP Backend Commons Documentation'

# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'hbp_nrp_commons', u'NRP Backend Commons Documentation',
     [u'hinkel'], 1)
]

# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'hbp_nrp_commons', u'NRP Backend Commons Documentation',
   u'hinkel', 'hbp_nrp_commons', 'Common functionality shared in the backend',
   'Neurorobotics'),
]

autodoc_mock_imports = ['nrp_core']
