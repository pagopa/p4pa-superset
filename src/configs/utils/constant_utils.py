import os

class SupersetRoleNameConstants:
    __SUPERSET_OPERATOR_ROLE_NAME = "operator_access_role"
    __SUPERSET_ORGANIZATION_ADMIN_ROLE_NAME = "organization_admin_access_role"
    __SUPERSET_BROKER_ADMIN_ROLE_NAME = "broker_admin_access_role"
    __SUPERSET_DEFAULT_ROLE_NAME = "default_access_role"

    @staticmethod
    def getSupersetOperatorRoleName():
        return SupersetRoleNameConstants.__SUPERSET_OPERATOR_ROLE_NAME

    @staticmethod
    def getSupersetOrganizationAdminRoleName():
        return SupersetRoleNameConstants.__SUPERSET_ORGANIZATION_ADMIN_ROLE_NAME

    @staticmethod
    def getSupersetBrokerAdminRoleName():
        return SupersetRoleNameConstants.__SUPERSET_BROKER_ADMIN_ROLE_NAME

    @staticmethod
    def getSupersetDefaultRoleName():
        return SupersetRoleNameConstants.__SUPERSET_DEFAULT_ROLE_NAME

class PURoleNameConstants:
    __PU_OPERATOR_ROLE_NAME = "ROLE_OPER"
    __PU_ROLE_ADMIN_NAME = "ROLE_ADMIN"

    @staticmethod
    def getPUOperatorRoleName():
        return PURoleNameConstants.__PU_OPERATOR_ROLE_NAME

    @staticmethod
    def getPUAdminRoleName():
        return PURoleNameConstants.__PU_ROLE_ADMIN_NAME

class DBConstants:
    __ANALYTICS_DB_NAME = os.environ.get('ANALYTICS_DB_NAME')
    __ANALYTICS_DB_SCHEMA_NAME = os.environ.get('ANALYTICS_DB_SCHEMA_NAME')

    @staticmethod
    def getAnalyticsDbName():
        return DBConstants.__ANALYTICS_DB_NAME

    @staticmethod
    def getAnalyticsDbSchemaName():
        return DBConstants.__ANALYTICS_DB_SCHEMA_NAME

class ConnectorConstants:
    __DEBT_POSITIONS_TYPE_ORG_URL = os.environ.get(
        'DEBT_POSITIONS_BASE_URL') + "/crud/debt-position-type-orgs/search/findDebtPositionTypeOrgs"

    @staticmethod
    def getDebtPositionsTypeOrgURL():
        return ConnectorConstants.__DEBT_POSITIONS_TYPE_ORG_URL

class SupersetResourcePrefixConstants:
    __SUPERSET_RLS_PREFIX = "rls_"
    __SUPERSET_ROLE_PREFIX = "role_"

    @staticmethod
    def getSupersetRLSPrefix():
        return SupersetResourcePrefixConstants.__SUPERSET_RLS_PREFIX

    @staticmethod
    def getSupersetRolePrefix():
        return SupersetResourcePrefixConstants.__SUPERSET_ROLE_PREFIX