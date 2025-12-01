import logging
import os
from superset.security import SupersetSecurityManager
from rls_manager import RlsManager
from db_utils import SupersetDatabaseUtils
from pu_user_info_dto import PUUserInfo
from configuration_utils import ConfigurationUtils

ANALYTICS_DB_NAME = os.environ.get('ANALYTICS_DB_NAME')
ANALYTICS_DB_SCHEMA_NAME = os.environ.get('ANALYTICS_DB_SCHEMA_NAME')

logger = logging.getLogger(__name__)

class RoleAndPermissionManager:
    def __init__(self):
        self.rls_manager = RlsManager()

    def manage_user_roles_and_permissions(self, sm: SupersetSecurityManager, user, pu_user_info: PUUserInfo, http_headers):
        user.roles = [role for role in user.roles if role.name not in ConfigurationUtils.getPUSupersetRoleList()]
        self.__create_and_assign_role_to_user(sm, f"role_{pu_user_info.id}", user)
        self.__assign_datasource_permissions_to_user(sm, pu_user_info, user)
        self.rls_manager.upsert_rls(sm, pu_user_info, http_headers)

    def __create_and_assign_role_to_user(self, sm: SupersetSecurityManager, pu_role, user):
        role = sm.add_role(pu_role)
        self.__assign_role_to_user(sm, role, user)
        return role

    def __assign_role_to_user(self, sm: SupersetSecurityManager, role, user):
        if role not in user.roles:
            logger.info(f'Assigning role {role} to user {user.username}')
            user.roles.append(role)
            sm.update_user(user)
            logger.info(f'Assigned role {role} to user {user.username}')

    def __assign_datasource_permissions_to_user(self, sm: SupersetSecurityManager, pu_user_info: PUUserInfo, user):
        if self.__is_operator(pu_user_info):
            role = self.__create_and_assign_role_to_user(sm, "operator_access_role", user)
            self.__assign_datasource_permissions_to_role(sm, ConfigurationUtils.getOperatorDatasourceNameList(), role)
        elif self.__is_organization_admin(pu_user_info):
            role = self.__create_and_assign_role_to_user(sm, "organization_admin_access_role", user)
            self.__assign_datasource_permissions_to_role(sm, ConfigurationUtils.getOrganizationAdminDatasourceNameList(), role)
        elif self.__is_broker_admin(pu_user_info):
            role = self.__create_and_assign_role_to_user(sm, "broker_admin_access_role", user)
            self.__assign_datasource_permissions_to_role(sm, ConfigurationUtils.getBrokerAdminDatasourceNameList(), role)
        else:
            role = self.__create_and_assign_role_to_user(sm, "default_access_role", user)
            self.__assign_datasource_permissions_to_role(sm, ConfigurationUtils.getDefaultDatasourceNameList(), role)

    def __is_operator(self, pu_user_info: PUUserInfo):
        if "ROLE_OPERATOR" in pu_user_info.user_roles and "ROLE_ADMIN" not in pu_user_info.user_roles:
            return True
        else:
            return False

    def __is_organization_admin(self, pu_user_info: PUUserInfo):
        if "ROLE_ADMIN" in pu_user_info.user_roles and pu_user_info.organization_code != pu_user_info.broker_code:
            return True
        else:
            return False

    def __is_broker_admin(self, pu_user_info: PUUserInfo):
        if "ROLE_ADMIN" in pu_user_info.user_roles and pu_user_info.organization_code == pu_user_info.broker_code:
            return True
        else:
            return False

    def __assign_datasource_permissions_to_role(self, sm: SupersetSecurityManager, datasource_name_list, role):
        view_menu_name_list = []
        for datasource_name in datasource_name_list:
            datasource = SupersetDatabaseUtils.fetch_superset_datasource(ANALYTICS_DB_NAME, ANALYTICS_DB_SCHEMA_NAME, datasource_name)
            if datasource:
                view_menu_name_list.append(self.__build_view_menu_name(datasource))
                self.__assign_datasource_permission_to_role(sm, datasource, role)
        for perm_view in role.permissions:
            if perm_view.view_menu.name not in view_menu_name_list:
                sm.del_permission_role(role, perm_view)

    def __assign_datasource_permission_to_role(self, sm: SupersetSecurityManager, datasource, role):
        logger.info(f'Assigning permission for accessing datasource {datasource.name} to role {role.name}')
        permission_name = "datasource_access"
        view_menu_name =  self.__build_view_menu_name(datasource)
        permission_view = sm.find_permission_view_menu(permission_name, view_menu_name)
        if not permission_view:
            logger.warning(f"Permission view menu for {permission_name} {view_menu_name} not found.")
            return
        sm.add_permission_role(role, permission_view)
        logger.info(f'Assigned permission {view_menu_name} for accessing datasource {datasource.name} to role {role.name}')

    def __build_view_menu_name(self, datasource):
        return f"[{ANALYTICS_DB_NAME}].[{datasource.name.split(ANALYTICS_DB_SCHEMA_NAME + '.')[1]}](id:{datasource.id})"