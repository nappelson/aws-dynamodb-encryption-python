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
"""Cryptographic materials to use ephemeral content encryption keys wrapped by delegated keys."""
from __future__ import division
import base64
import copy

import attr

from dynamodb_encryption_sdk.delegated_keys import DelegatedKey
from dynamodb_encryption_sdk.delegated_keys.jce import JceNameLocalDelegatedKey
from dynamodb_encryption_sdk.exceptions import UnwrappingError, WrappingError
from dynamodb_encryption_sdk.identifiers import EncryptionKeyTypes
from dynamodb_encryption_sdk.internal.identifiers import MaterialDescriptionKeys
from dynamodb_encryption_sdk.materials import CryptographicMaterials

__all__ = ('WrappedRawCryptographicMaterials',)
_DEFAULT_CONTENT_ENCRYPTION_ALGORITHM = 'AES/256'
_WRAPPING_TRANSFORMATION = {
    'AES': 'AESWrap',
    'RSA': 'RSA/ECB/OAEPWithSHA-256AndMGF1Padding'
}


@attr.s(hash=False)
class WrappedCryptographicMaterials(CryptographicMaterials):
    """Encryption/decryption key is a content key stored in the material description, wrapped
    by the wrapping key.

    :param signing_key: Delegated key used as signing and verification key
    :type signing_key: dynamodb_encryption_sdk.delegated_keys.DelegatedKey
    :param wrapping_key: Delegated key used to wrap content key
    :type wrapping_key: dynamodb_encryption_sdk.delegated_keys.DelegatedKey

    .. note::

        ``wrapping_key`` must be provided if material description contains a wrapped content key

    :param unwrapping_key: Delegated key used to unwrap content key
    :type unwrapping_key: dynamodb_encryption_sdk.delegated_keys.DelegatedKey

    .. note::

        ``unwrapping_key`` must be provided if material description does not contain a wrapped content key

    :param dict material_description: Material description to use with these cryptographic materials
    """
    _signing_key = attr.ib(validator=attr.validators.instance_of(DelegatedKey))
    _wrapping_key = attr.ib(
        validator=attr.validators.optional(attr.validators.instance_of(DelegatedKey)),
        default=None
    )
    _unwrapping_key = attr.ib(
        validator=attr.validators.optional(attr.validators.instance_of(DelegatedKey)),
        default=None
    )
    _material_description = attr.ib(
        validator=attr.validators.instance_of(dict),
        converter=copy.deepcopy,
        default=attr.Factory(dict)
    )

    def __attrs_post_init__(self):
        """Prepare the content key."""
        self._content_key_algorithm = self.material_description.get(
            MaterialDescriptionKeys.CONTENT_ENCRYPTION_ALGORITHM.value,
            _DEFAULT_CONTENT_ENCRYPTION_ALGORITHM
        )

        if MaterialDescriptionKeys.WRAPPED_DATA_KEY.value in self.material_description:
            self._content_key = self._content_key_from_material_description()
        else:
            self._content_key, self._material_description = self._generate_content_key()

    def _wrapping_transformation(self, algorithm):
        """Convert the specified algorithm name to the desired wrapping algorithm transformation.

        :param str algorithm: Algorithm name
        :returns: Algorithm transformation for wrapping with algorithm
        :rtype: str
        """
        return _WRAPPING_TRANSFORMATION.get(algorithm, algorithm)

    def _content_key_from_material_description(self):
        """Load the content key from material description and unwrap it for use.

        :returns: Unwrapped content key
        :rtype: dynamodb_encryption_sdk.delegated_keys.DelegatedKey
        """
        if self._unwrapping_key is None:
            raise UnwrappingError(
                'Cryptographic materials cannot be loaded from material description: no unwrapping key'
            )

        wrapping_algorithm = self.material_description.get(
            MaterialDescriptionKeys.CONTENT_KEY_WRAPPING_ALGORITHM.value,
            self._unwrapping_key.algorithm
        )
        wrapped_key = base64.b64decode(
            self.material_description[MaterialDescriptionKeys.WRAPPED_DATA_KEY.value]
        )
        content_key_algorithm = self._content_key_algorithm.split('/', 1)[0]
        return self._unwrapping_key.unwrap(
            algorithm=wrapping_algorithm,
            wrapped_key=wrapped_key,
            wrapped_key_algorithm=content_key_algorithm,
            wrapped_key_type=EncryptionKeyTypes.SYMMETRIC,
            additional_associated_data=None
        )

    def _generate_content_key(self):
        """Generate the content encryption key and create a new material description containing
        necessary information about the content and wrapping keys.

        :returns content key and new material description
        :rtype: tuple containing dynamodb_encryption_sdk.delegated_keys.DelegatedKey and dict
        """
        if self._wrapping_key is None:
            raise WrappingError('Cryptographic materials cannot be generated: no wrapping key')

        wrapping_algorithm = self.material_description.get(
            MaterialDescriptionKeys.CONTENT_KEY_WRAPPING_ALGORITHM.value,
            self._wrapping_transformation(self._wrapping_key.algorithm)
        )
        args = self._content_key_algorithm.split('/', 1)
        content_algorithm = args[0]
        try:
            content_key_length = int(args[1]) // 8
        except IndexError:
            content_key_length = None
        content_key = JceNameLocalDelegatedKey.generate(
            algorithm=content_algorithm,
            key_length=content_key_length
        )
        wrapped_key = self._wrapping_key.wrap(
            algorithm=wrapping_algorithm,
            content_key=content_key.key,
            additional_associated_data=None
        )
        new_material_description = self.material_description.copy()
        new_material_description.update({
            MaterialDescriptionKeys.WRAPPED_DATA_KEY.value: base64.b64encode(wrapped_key),
            MaterialDescriptionKeys.CONTENT_ENCRYPTION_ALGORITHM.value: self._content_key_algorithm,
            MaterialDescriptionKeys.CONTENT_KEY_WRAPPING_ALGORITHM.value: wrapping_algorithm
        })
        return content_key, new_material_description

    @property
    def material_description(self):
        # type: () -> Dict[Text, Text]
        """Material description to use with these cryptographic materials.

        :returns: Material description
        :rtype: dict
        """
        return self._material_description

    @property
    def encryption_key(self):
        """Content key used for encrypting attributes.

        :returns: Encryption key
        :rtype: dynamodb_encryption_sdk.delegated_keys.DelegatedKey
        """
        return self._content_key

    @property
    def decryption_key(self):
        """Content key used for decrypting attributes.

        :returns: Decryption key
        :rtype: dynamodb_encryption_sdk.delegated_keys.DelegatedKey
        """
        return self._content_key

    @property
    def signing_key(self):
        """Delegated key used for calculating digital signatures.

        :returns: Signing key
        :rtype: dynamodb_encryption_sdk.delegated_keys.DelegatedKey
        """
        return self._signing_key

    @property
    def verification_key(self):
        """Delegated key used for verifying digital signatures.

        :returns: Verification key
        :rtype: dynamodb_encryption_sdk.delegated_keys.DelegatedKey
        """
        return self._signing_key
