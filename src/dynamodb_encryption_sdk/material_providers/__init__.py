# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Cryptographic materials providers."""
from dynamodb_encryption_sdk.materials import DecryptionMaterials, EncryptionMaterials
from dynamodb_encryption_sdk.structures import EncryptionContext


class CryptographicMaterialsProvider(object):
    """Base class for all cryptographic materials providers."""

    def decryption_materials(self, encryption_context):
        # type: (EncryptionContext) -> DecryptionMaterials
        """Return decryption materials.

        :param encryption_context: Encryption context for request
        :type encryption_context: dynamodb_encryption_sdk.structures.EncryptionContext
        :raises AttributeError: if no decryption materials are available
        """
        raise AttributeError('No decryption materials available')

    def encryption_materials(self, encryption_context):
        # type: (EncryptionContext) -> EncryptionMaterials
        """Return encryption materials.

        :param encryption_context: Encryption context for request
        :type encryption_context: dynamodb_encryption_sdk.structures.EncryptionContext
        :raises AttributeError: if no encryption materials are available
        """
        raise AttributeError('No encryption materials available')

    def refresh(self):
        """Ask this instance to refresh the cryptographic materials.

        .. note::

            Default behavior is to do nothing.
        """
