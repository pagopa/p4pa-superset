import logging
import os
from superset.security import SupersetSecurityManager
from flask import flash
import requests
from flask_appbuilder.security.views import UserDBModelView,AuthDBView
from flask_appbuilder.security.views import expose
from flask_appbuilder.security.manager import BaseSecurityManager
from flask_login import login_user, logout_user
from flask import g, request, redirect

USERINFO_URL = 'https://api.dev.p4pa.pagopa.it/pu/auth/oauth/userinfo' # os.environ.get('AUTH_BASE_URL') + "/oauth/userinfo"
logger = logging.getLogger(__name__)
class CustomAuthView(AuthDBView):
  @expose('/sso-login/', methods=['GET','POST'])
  def login(self):
    jwt_token = request.args.get('token')
    if not jwt_token:
      return super(CustomAuthView,self).login()
    if jwt_token:
            try:
                headers = {'Authorization': f'Bearer {jwt_token}'}
                response = requests.get(USERINFO_URL, headers=headers, timeout=5, verify=False)
                response.raise_for_status()
                user_data = response.json()
                user_identifier = user_data.get('mappedExternalUserId')
                if user_identifier:
                    sm = self.appbuilder.sm
                    user = sm.find_user(username=user_identifier)
                    if not user and sm.auth_user_registration:
                        first_name = user_data.get('name')
                        last_name =  user_data.get('familyName')
                        email = ''
                        role = sm.find_role(sm.auth_user_registration_role)
                        user = sm.add_user(user_identifier, first_name, last_name, email, role)
                    if user:
                        login_user(user, remember=False)
                        return redirect(self.appbuilder.get_url_for_index)
                    else:
                         logger.debug('Utente non trovato e registrazione non permessa.')
            except Exception as e:
                logger.debug('Errore generico nel login SSO: %s',e)
    else:
      logger.debug('Unable to auto login')
      return super(CustomAuthView,self).login()

class CustomSecurityManager(SupersetSecurityManager):
    authdbview = CustomAuthView
    def __init__(self, appbuilder):
        super(CustomSecurityManager, self).__init__(appbuilder)