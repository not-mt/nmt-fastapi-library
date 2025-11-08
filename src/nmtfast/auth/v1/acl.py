# -*- coding: utf-8 -*-
# Copyright (c) 2025. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for details.

"""Library classes and functions to handle client authorization."""

import logging
import re

from pydantic import BaseModel, field_serializer

from nmtfast.auth.v1.exceptions import AuthorizationError
from nmtfast.settings.v1.schemas import SectionACL

logger = logging.getLogger(__name__)


class AuthSuccess(BaseModel):
    """
    Results of a successful authentication.

    Attributes:
        name: API Key or OAuth client name that was authenticated.
        acls: List of section access control rules.
    """

    name: str
    acls: list[SectionACL]

    @field_serializer("acls")
    def serialize_acls(self, acls: list[SectionACL], _info):
        """
        Custom serializer for converting objects to JSON objects.
        """
        return [acl.model_dump() for acl in acls]


async def check_acl(
    section: str,
    acls: list[SectionACL],
    method: str,
    payload: dict = dict(),
    raise_on_failure: bool = True,
) -> bool:
    """
    Checks if a client is permitted to access a section based on provided ACLs.

    This function iterates through the provided Access Control Lists (ACLs) to determine
    if the client has the necessary permissions to access the specified section using
    the given HTTP method or operation.

    Args:
        section: The section of the resource being accessed (e.g., "widgets", "users").
        acls: A list of SectionACL objects representing the client's access permissions.
        method: The method or operation being performed (e.g., "view", "edit", "delete").
        payload: An optional dictionary representing the request body or payload.
        raise_on_failure: If True, raises AuthorizationError on access denial.

    Returns:
        bool: True if the client is permitted to access the section, False otherwise.

    Raises:
        AuthorizationError: If access is denied and raise_on_failure is True.
    """
    for acl in acls:
        section_regex = acl.section_regex
        permissions = acl.permissions
        filters: list = []  # TODO: implement filters later

        # continue if the section does not apply
        if section_regex and not re.match(section_regex, section):
            continue

        # allow if the section matched, and * is in the and filters is empty
        if "*" in permissions and not filters:
            logger.debug("Allow '*' and empty filter list")
            return True

        # allow if the specific permission is granted
        if "*" not in permissions and method in permissions:
            logger.debug(f"Allow method '{method}': permissions: {permissions}")
            return True

        # TODO: add support for filters later
        # for filter_ in filters:
        #     action = filter_.get("action")
        #     scope = filter_.get("scope")
        #     field = filter_.get("field")
        #     match_regex = filter_.get("match_regex")
        #
        #     if action == "allow" and scope == "payload" and field and match_regex:
        #         if payload and field in payload:
        #             if re.match(match_regex, str(payload[field])):
        #                 logger.debug(f"Filter matched '{match_regex}' to '{str(payload[field])}'")
        #                 return True  # filter matched
        #     else:
        #         logger.debug("Filter did not match")
        #         return False  # filter specified a field that does not exist in the payload.

        logger.debug("All filters failed")
        if raise_on_failure:
            raise AuthorizationError(
                f"Access denied: No ACLs granted '{method}' permission "
                f"for '{section}' section!"
            )

        return False  # all filters failed, access denied

    logger.debug("No sections matched")
    if raise_on_failure:
        raise AuthorizationError(
            f"Access denied: no ACLs matches for '{section}' section!"
        )

    return False  # no matching section or permission
