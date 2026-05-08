from configs.utils.constant_utils import SupersetRoleNameConstants
from configs.utils.role_utils import SupersetRole, SupersetRoleUtils
from configs.utils.db_utils import DatasourceEnum
from configs.dto.pu_user_info_dto import PUUserInfo

class PermissionUtils:
    __DEFAULT_DATASOURCE_ACCESS_PERMISSION_SET: set[str] = {}
    __OPERATOR_DATASOURCE_ACCESS_PERMISSION_SET: set[str] = {DatasourceEnum.ASSESSMENT_CLASSIFICATION}
    __ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_SET: set[str] = {DatasourceEnum.ASSESSMENT_CLASSIFICATION, DatasourceEnum.ACCESS_MONITORING, DatasourceEnum.FLOW_FILE_MONITORING}
    __BROKER_ADMIN_DATASOURCE_ACCESS_PERMISSION_SET: set[str] = {DatasourceEnum.ASSESSMENT_CLASSIFICATION, DatasourceEnum.ACCESS_MONITORING, DatasourceEnum.FLOW_FILE_MONITORING}

    @staticmethod
    def getUserRoleDatasourcePermissionSet(pu_user_info: PUUserInfo) -> set[str]:
        user_role: SupersetRole = SupersetRoleUtils.get_user_role(pu_user_info)
        match user_role:
            case SupersetRole.OPERATOR:
                return PermissionUtils.__getOperatorDatasourcePermissionSet()
            case SupersetRole.ORGANIZATION_ADMIN:
                return PermissionUtils.__getOrganizationAdminDatasourcePermissionSet()
            case SupersetRole.BROKER_ADMIN:
                return PermissionUtils.__getBrokerAdminDatasourcePermissionSet()
            case _:
                return PermissionUtils.__getDefaultDatasourcePermissionSet()

    @staticmethod
    def __getOperatorDatasourcePermissionSet() -> set[str]:
        return PermissionUtils.__OPERATOR_DATASOURCE_ACCESS_PERMISSION_SET

    @staticmethod
    def __getOrganizationAdminDatasourcePermissionSet() -> set[str]:
        return PermissionUtils.__ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_SET

    @staticmethod
    def __getBrokerAdminDatasourcePermissionSet() -> set[str]:
        return PermissionUtils.__BROKER_ADMIN_DATASOURCE_ACCESS_PERMISSION_SET

    @staticmethod
    def __getDefaultDatasourcePermissionSet() -> set[str]:
        return PermissionUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_SET