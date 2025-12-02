import os
from configs.utils.constant_utils import ConstantUtils

class ConfigurationUtils:
    __OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST_STRING = "v_assessment_classified"
    __ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST_STRING = ""
    __BROKER_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST_STRING = ""
    __DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST_STRING = ""

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
            ConfigurationUtils.__OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST_STRING + ',' +
            ConfigurationUtils.__ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST_STRING + ',' +
            ConfigurationUtils.__BROKER_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST_STRING + ',' +
            ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST_STRING
        ).split(","))

    @staticmethod
    def getOperatorDatasourceNameList():
        return set((
            ConfigurationUtils.__OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST_STRING + ',' +
            ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST_STRING
        ).split(","))

    @staticmethod
    def getOrganizationAdminDatasourceNameList():
        return set((
            ConfigurationUtils.__OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST_STRING + ',' +
            ConfigurationUtils.__ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST_STRING + ',' +
            ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST_STRING
        ).split(","))

    @staticmethod
    def getBrokerAdminDatasourceNameList():
        return set((
            ConfigurationUtils.__OPERATOR_DATASOURCE_ACCESS_PERMISSION_LIST_STRING + ',' +
            ConfigurationUtils.__ORGANIZATION_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST_STRING + ',' +
            ConfigurationUtils.__BROKER_ADMIN_DATASOURCE_ACCESS_PERMISSION_LIST_STRING + ',' +
            ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST_STRING
        ).split(","))

    @staticmethod
    def getDefaultDatasourceNameList():
        return ConfigurationUtils.__DEFAULT_DATASOURCE_ACCESS_PERMISSION_LIST_STRING