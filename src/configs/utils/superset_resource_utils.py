class SupersetResourceUtils:

    @staticmethod
    def build_view_menu_name(analytics_db_name, analytics_db_schema_name, datasource):
        return f"[{analytics_db_name}].[{datasource.name.split(analytics_db_schema_name + '.')[1]}](id:{datasource.id})"

    @staticmethod
    def find_permission_view_menu(sm, analytics_db_name, analytics_db_schema_name, datasource):
        permission_name = "datasource_access"
        view_menu_name = SupersetResourceUtils.build_view_menu_name(analytics_db_name, analytics_db_schema_name, datasource)
        return sm.find_permission_view_menu(permission_name, view_menu_name)

    @staticmethod
    def build_rls_for_org_id_and_debt_position_type_org_id(organization_id, debt_position_type_org_ids_string):
        return f"organization_id = '{organization_id}' and debt_position_type_org_id in ({debt_position_type_org_ids_string})"