import os
from configs.utils.constant_utils import ConstantUtils

class ConfigurationUtils:
    __OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST = os.environ.get("OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST")
    __ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST = os.environ.get("ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST")
    __BROKER_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST = os.environ.get("BROKER_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST")
    __DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST = os.environ.get("DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST")

    __pu_superset_roles = [
        ConstantUtils.getSupersetOperatorRoleName(),
        ConstantUtils.getSupersetOrganizationAdminRoleName(),
        ConstantUtils.getSupersetBrokerAdminRoleName(),
        ConstantUtils.getSupersetDefaultRoleName()
    ]

    @staticmethod
    def getPUSupersetRoleList():
        return ConfigurationUtils.__pu_superset_roles

    @staticmethod
    def getAllDatasourceNameList():
        return set((
            ConfigurationUtils.__OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST + ',' +
            ConfigurationUtils.__ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST + ',' +
            ConfigurationUtils.__BROKER_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST + ',' +
            ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST
        ).split(","))

    @staticmethod
    def getOperatorDatasourceNameList():
        return set((
            ConfigurationUtils.__OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST + ',' +
            ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST
        ).split(","))

    @staticmethod
    def getOrganizationAdminDatasourceNameList():
        return set((
            ConfigurationUtils.__OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST + ',' +
            ConfigurationUtils.__ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST + ',' +
            ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST
        ).split(","))

    @staticmethod
    def getBrokerAdminDatasourceNameList():
        return set((
            ConfigurationUtils.__OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST + ',' +
            ConfigurationUtils.__ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST + ',' +
            ConfigurationUtils.__BROKER_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST + ',' +
            ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST
        ).split(","))

    @staticmethod
    def getDefaultDatasourceNameList():
        return ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST