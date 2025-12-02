from configs.utils.constant_utils import ConstantUtils

class ConfigurationUtils:
    __DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST = []
    __OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST = ["v_assessment_classified"]
    __ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST = []
    __BROKER_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST = []

    __ORG_ID_AND_DP_TYPE_ORG_ID_RLS_APPLY_TO_DATASOURCE_LIST = ["debt_position_type_orgs"]

    __pu_superset_roles = [
        ConstantUtils.getSupersetDefaultRoleName(),
        ConstantUtils.getSupersetOperatorRoleName(),
        ConstantUtils.getSupersetOrganizationAdminRoleName(),
        ConstantUtils.getSupersetBrokerAdminRoleName()
    ]

    @staticmethod
    def getPUSupersetRoleList():
        return ConfigurationUtils.__pu_superset_roles

    @staticmethod
    def getOrgIdAndDebtPositionTypeOrgIdRLSApplyToDatasourceList():
        return set(
            ConfigurationUtils.__ORG_ID_AND_DP_TYPE_ORG_ID_RLS_APPLY_TO_DATASOURCE_LIST
        )

    @staticmethod
    def getAllDatasourceNameList():
        return set(
            ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST +
            ConfigurationUtils.__OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST +
            ConfigurationUtils.__ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST +
            ConfigurationUtils.__BROKER_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST
        )

    @staticmethod
    def getOperatorDatasourceNameList():
        return set(
            ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST +
            ConfigurationUtils.__OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST
        )

    @staticmethod
    def getOrganizationAdminDatasourceNameList():
        return set(
            ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST +
            ConfigurationUtils.__OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST +
            ConfigurationUtils.__ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST
        )

    @staticmethod
    def getBrokerAdminDatasourceNameList():
        return set(
            ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST +
            ConfigurationUtils.__OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST +
            ConfigurationUtils.__ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST +
            ConfigurationUtils.__BROKER_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST
        )

    @staticmethod
    def getDefaultDatasourceNameList():
        return set(ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST)