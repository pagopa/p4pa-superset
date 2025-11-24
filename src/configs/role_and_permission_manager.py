import logging
import os
from superset.security import SupersetSecurityManager
from configs.rls_manager import RlsManager

ANALYTICS_DB_NAME = os.environ.get('ANALYTICS_DB_NAME')
SCHEMA_AND_TABLE_NAME_LIST_STRING = os.environ.get("SCHEMA_AND_TABLE_NAME_LIST_STRING")
logger = logging.getLogger(__name__)

class RoleAndPermissionManager:
    def __init__(self):
        self.rls_manager = RlsManager()

    def manage_user_roles_and_permissions(self, sm: SupersetSecurityManager, user_identifier, user, organization_id, http_headers):
        role = sm.add_role(f"role_{user_identifier}")
        self.__assign_role_to_user(sm, role, user)
        role = sm.add_role("operator_access_role")
        self.__assign_role_to_user(sm, role, user)
        for schema in self.__extract_schema_name_set(SCHEMA_AND_TABLE_NAME_LIST_STRING.split(",")):
            self.__assign_schema_permission(sm, schema, role)
        self.rls_manager.upsert_rls(user_identifier, organization_id, http_headers)

    def __assign_role_to_user(self, sm: SupersetSecurityManager, role, user):
        if role not in user.roles:
            logger.info(f'Assigning role {role} to user {user.username}')
            user.roles.append(role)
            sm.update_user(user)

    def __extract_schema_name_set(self, schema_and_table_name_list):
        return set([schema_and_table_name.split("|")[0] for schema_and_table_name in schema_and_table_name_list])

    def __assign_schema_permission(self, sm: SupersetSecurityManager, schema, role):
        logger.info(f'Checking permission for accessing schema {schema} to role {role.name}')
        permission_name = "schema_access"
        view_menu_name = f"[{ANALYTICS_DB_NAME}].[{ANALYTICS_DB_NAME}].[{schema}]"
        permission_view_menu = sm.find_permission_view_menu(permission_name, view_menu_name)
        if not permission_view_menu:
            logger.warning(f"Permission view menu for {permission_name} {view_menu_name} not found.")
            return
        if permission_view_menu.id in [permission.id for permission in role.permissions]:
            logger.info(f'Permission for accessing schema {schema} to role {role.name} already assigned.')
            return
        sm.add_permission_role(role, permission_view_menu)
        logger.info(f'Assigned permission for accessing schema {schema} to role {role.name}')