import logging
from superset.security import SupersetSecurityManager
from configs.rls_manager import RlsManager
from configs.dto.pu_user_info_dto import PUUserInfo
from configs.utils.db_utils import SupersetDatabaseUtils
from configs.utils.configuration_utils import ConfigurationUtils
from configs.utils.constant_utils import ConstantUtils
from configs.utils.superset_resource_utils import SupersetResourceUtils
from configs.utils.pu_role_utils import PURoleUtils

ANALYTICS_DB_NAME = ConstantUtils.getAnalyticsDbName()
ANALYTICS_DB_SCHEMA_NAME = ConstantUtils.getAnalyticsDbSchemaName()

logger = logging.getLogger(__name__)

class RoleAndPermissionManager:
    def __init__(self):
        self.rls_manager = RlsManager()

    def manage_user_roles_and_permissions(self, sm: SupersetSecurityManager, user, pu_user_info: PUUserInfo, http_headers):
        user.roles = [role for role in user.roles if role.name not in ConfigurationUtils.getPUSupersetRoleList()] #removing previous logged role for granting correct permissions
        logged_user_role = ConstantUtils.getSupersetRolePrefix() + pu_user_info.id
        self.__create_and_assign_role_to_user(sm, logged_user_role, user)
        self.__assign_datasource_permissions_to_user(sm, pu_user_info, user)
        self.rls_manager.upsert_all_rls(sm, pu_user_info, http_headers)

    def __create_and_assign_role_to_user(self, sm: SupersetSecurityManager, superset_role, user):
        role = sm.add_role(superset_role)
        self.__assign_role_to_user(sm, role, user)
        return role

    def __assign_role_to_user(self, sm: SupersetSecurityManager, role, user):
        if role not in user.roles:
            logger.info(f'Assigning role {role} to user {user.username}')
            user.roles.append(role)
            sm.update_user(user)
            logger.info(f'Assigned role {role} to user {user.username}')

    def __assign_datasource_permissions_to_user(self, sm: SupersetSecurityManager, pu_user_info: PUUserInfo, user):
        if PURoleUtils.is_operator(pu_user_info):
            role = self.__create_and_assign_role_to_user(sm, ConstantUtils.getSupersetOperatorRoleName(), user)
            self.__assign_datasource_permissions_to_role(sm, ConfigurationUtils.getOperatorDatasourceNameList(), role)
        elif PURoleUtils.is_organization_admin(pu_user_info):
            role = self.__create_and_assign_role_to_user(sm, ConstantUtils.getSupersetOrganizationAdminRoleName(), user)
            self.__assign_datasource_permissions_to_role(sm, ConfigurationUtils.getOrganizationAdminDatasourceNameList(), role)
        elif PURoleUtils.is_broker_admin(pu_user_info):
            role = self.__create_and_assign_role_to_user(sm, ConstantUtils.getSupersetBrokerAdminRoleName(), user)
            self.__assign_datasource_permissions_to_role(sm, ConfigurationUtils.getBrokerAdminDatasourceNameList(), role)
        else:
            role = self.__create_and_assign_role_to_user(sm, ConstantUtils.getSupersetDefaultRoleName(), user)
            self.__assign_datasource_permissions_to_role(sm, ConfigurationUtils.getDefaultDatasourceNameList(), role)

    def __assign_datasource_permissions_to_role(self, sm: SupersetSecurityManager, datasource_name_list, role):
        view_menu_name_list = []
        for datasource_name in datasource_name_list:
            datasource = SupersetDatabaseUtils.fetch_superset_datasource(ANALYTICS_DB_NAME, ANALYTICS_DB_SCHEMA_NAME, datasource_name)
            if datasource:
                view_menu_name_list.append(SupersetResourceUtils.build_view_menu_name(ANALYTICS_DB_NAME, ANALYTICS_DB_SCHEMA_NAME, datasource))
                self.__assign_datasource_permission_to_role(sm, datasource, role)
        for perm_view in role.permissions:
            if perm_view.view_menu.name not in view_menu_name_list:
                sm.del_permission_role(role, perm_view)

    def __assign_datasource_permission_to_role(self, sm: SupersetSecurityManager, datasource, role):
        logger.info(f'Assigning permission for accessing datasource {datasource.name} to role {role.name}')
        permission_view = SupersetResourceUtils.find_permission_view_menu(sm, ANALYTICS_DB_NAME, ANALYTICS_DB_SCHEMA_NAME, datasource)
        if not permission_view:
            logger.warning(f"Permission view menu {permission_view} not found.")
            return
        sm.add_permission_role(role, permission_view)
        logger.info(f'Assigned permission {permission_view} to role {role.name}')