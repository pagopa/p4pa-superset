import logging
from superset.security import SupersetSecurityManager
from configs.rls_manager import RlsManager
from configs.dto.pu_user_info_dto import PUUserInfo
from configs.utils.db_utils import SupersetDatabaseUtils
from configs.utils.permission_utils import PermissionUtils
from configs.utils.constant_utils import DBConstants, SupersetResourcePrefixConstants
from configs.utils.superset_resource_utils import SupersetResourceUtils
from configs.utils.role_utils import SupersetRoleUtils

ANALYTICS_DB_NAME = DBConstants.getAnalyticsDbName()
ANALYTICS_DB_SCHEMA_NAME = DBConstants.getAnalyticsDbSchemaName()

logger = logging.getLogger(__name__)

class RoleAndPermissionManager:
    def __init__(self):
        self.rls_manager = RlsManager()

    def manage_user_roles_and_permissions(self, sm: SupersetSecurityManager, user, pu_user_info: PUUserInfo, http_headers):
        user.roles = [role for role in user.roles if role.name not in SupersetRoleUtils.getSupersetRoleSet()] #removing previous logged role for granting correct permissions
        logged_user_role = SupersetResourcePrefixConstants.getSupersetRolePrefix() + pu_user_info.id
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
        role = self.__create_and_assign_role_to_user(sm, SupersetRoleUtils.get_user_role(pu_user_info), user)
        self.__assign_datasource_permissions_to_role(sm, PermissionUtils.getUserRoleDatasourcePermissionSet(pu_user_info), role)

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