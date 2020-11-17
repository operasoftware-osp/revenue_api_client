# Copyright 2020 Opera Software International AS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import importlib
import os

from setuptools import setup

version_module = importlib.import_module("opera_revenue_api.version")
version = version_module.__version__

current_dir = os.path.dirname(__file__)
path = os.path.join(current_dir, "requirements.txt")


if os.path.exists(path):
    with open(path) as f:
        install_requirements = [l.strip() for l in f.readlines()]
else:
    install_requirements = []


setup(
    name="opera_revenue_api_client",
    version=version,
    license="Apache License 2.0",
    author="Opera Statistics Platform",
    author_email="statistics-dev@opera.com",
    description="Client for Opera Revenue API",
    packages=["opera_revenue_api"],
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    install_requires=install_requirements,
    entry_points={"console_scripts": ["opera_revenue_api_upload = opera_revenue_api.client:opera_revenue_api_upload"]},
)
