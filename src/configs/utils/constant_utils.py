import os

class ConstantUtils:
    __SUPERSET_OPERATOR_ROLE_NAME = "operator_access_role"
    __SUPERSET_ORGANIZATION_ADMIN_ROLE_NAME = "organization_admin_access_role"
    __SUPERSET_BROKER_ADMIN_ROLE_NAME = "broker_admin_access_role"
    __SUPERSET_DEFAULT_ROLE_NAME = "default_access_role"

    __PU_OPERATOR_ROLE_NAME = "ROLE_OPERATOR"
    __PU_ROLE_ADMIN_NAME = "ROLE_ADMIN"

    __DEBT_POSITIONS_TYPE_ORG_URL = os.environ.get('DEBT_POSITIONS_BASE_URL') + "/crud/debt-position-type-orgs/search/findDebtPositionTypeOrgs"

    __SUPERSET_RLS_PREFIX = "rls_"
    __SUPERSET_ROLE_PREFIX = "role_"

    __ANALYTICS_DB_NAME = os.environ.get('ANALYTICS_DB_NAME')
    __ANALYTICS_DB_SCHEMA_NAME = os.environ.get('ANALYTICS_DB_SCHEMA_NAME')

    @staticmethod
    def getAnalyticsDbName():
        return ConstantUtils.__ANALYTICS_DB_NAME

    @staticmethod
    def getAnalyticsDbSchemaName():
        return ConstantUtils.__ANALYTICS_DB_SCHEMA_NAME

    @staticmethod
    def getDebtPositionsTypeOrgURL():
        return ConstantUtils.__DEBT_POSITIONS_TYPE_ORG_URL

    @staticmethod
    def getSupersetRLSPrefix():
        return ConstantUtils.__SUPERSET_RLS_PREFIX

    @staticmethod
    def getSupersetRolePrefix():
        return ConstantUtils.__SUPERSET_ROLE_PREFIX

    @staticmethod
    def getPUOperatorRoleName():
        return ConstantUtils.__PU_OPERATOR_ROLE_NAME

    @staticmethod
    def getPUAdminRoleName():
        return ConstantUtils.__PU_ROLE_ADMIN_NAME

    @staticmethod
    def getSupersetOperatorRoleName():
        return ConstantUtils.__SUPERSET_OPERATOR_ROLE_NAME

    @staticmethod
    def getSupersetOrganizationAdminRoleName():
        return ConstantUtils.__SUPERSET_ORGANIZATION_ADMIN_ROLE_NAME

    @staticmethod
    def getSupersetBrokerAdminRoleName():
        return ConstantUtils.__SUPERSET_BROKER_ADMIN_ROLE_NAME

    @staticmethod
    def getSupersetDefaultRoleName():
        return ConstantUtils.__SUPERSET_DEFAULT_ROLE_NAME