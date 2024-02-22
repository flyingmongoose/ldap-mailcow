import sys, os, string, time, datetime
import ldap

import filedb, api

import base64

from string import Template
from pathlib import Path

import logging

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%d.%m.%y %H:%M:%S', level=logging.INFO)


def main():
    global config
    config = read_config()

    passdb_conf = read_dovecot_passdb_conf_template()
    plist_ldap = read_sogo_plist_ldap_template()
    extra_conf = read_dovecot_extra_conf()

    passdb_conf_changed = apply_config('conf/dovecot/ldap/passdb.conf', config_data=passdb_conf)
    extra_conf_changed = apply_config('conf/dovecot/extra.conf', config_data=extra_conf)
    plist_ldap_changed = apply_config('conf/sogo/plist_ldap', config_data=plist_ldap)

    if passdb_conf_changed or extra_conf_changed or plist_ldap_changed:
        logging.info(
            "One or more config files have been changed, please make sure to restart dovecot-mailcow and sogo-mailcow!")

    api.api_host = config['API_HOST']
    api.api_key = config['API_KEY']
    api.ava_attr = config['LDAP_AVA_ATTR']

    while (True):
        sync()
        interval = int(config['SYNC_INTERVAL'])
        logging.info(f"Sync finished, sleeping {interval} seconds before next cycle")
        time.sleep(interval)


def sync():
    try:
        ldap_connector = ldap.initialize(f"{config['LDAP_URI']}")
        ldap_connector.set_option(ldap.OPT_REFERRALS, 0)
        ldap_connector.simple_bind_s(config['LDAP_BIND_DN'], config['LDAP_BIND_DN_PASSWORD'])

        ldap_results = ldap_connector.search_s(config['LDAP_BASE_DN'], ldap.SCOPE_SUBTREE,
                                               config['LDAP_FILTER'],
                                               ['mail', 'cn', 'st', 'description', config['LDAP_AVA_ATTR'],
                                                'userAccountControl'])

        # exclude None items from results
        ldap_results = [i for i in ldap_results if i[0] is not None]

        ldap_results = map(lambda x: (
            x[1]['mail'][0].decode(),
            x[1]['cn'][0].decode(),
            '' if "description" not in x[1] else x[1]['description'][0].decode(),
            b'' if config['LDAP_AVA_ATTR'] not in x[1] else base64.b64encode(x[1][config['LDAP_AVA_ATTR']][0]),
            False if int(x[1]['userAccountControl'][0].decode()) & 0b10 else True), ldap_results)

        filedb.session_time = datetime.datetime.now()

        for (email, ldap_name, ldap_description, ldap_avatar, ldap_active) in ldap_results:

            api_custom_attr = {}
            (db_user_exists, db_user_active) = filedb.check_user(email)

            (api_user_exists, api_user_active, api_name, api_custom_attr['description'],
             api_custom_attr[config['LDAP_AVA_ATTR']]) = api.check_user(email)

            unchanged = True
            changed_custom = False

            if not db_user_exists:
                filedb.add_user(email, ldap_active)
                (db_user_exists, db_user_active) = (True, ldap_active)
                logging.info(f"Added filedb user: {email} (Active: {ldap_active})")
                unchanged = False

            if not api_user_exists:
                api.add_user(email, ldap_name, ldap_active)
                api_custom_attr = {}
                (api_user_exists, api_user_active, api_name, api_custom_attr['description'],
                 api_custom_attr[config['LDAP_AVA_ATTR']]) = (
                True, ldap_active, ldap_name, ldap_description, ldap_avatar)
                logging.info(f"Added Mailcow user: {email} (Active: {ldap_active})")
                unchanged = False
                pass

            if db_user_active != ldap_active:
                filedb.user_set_active_to(email, ldap_active)
                logging.info(f"{'Activated' if ldap_active else 'Deactived'} {email} in filedb")
                unchanged = False

            if api_user_active != ldap_active:
                api.edit_user(email, name=ldap_name, active=ldap_active)
                logging.info(f"{'Activated' if ldap_active else 'Deactived'} {email} in Mailcow")
                unchanged = False

            if api_name != ldap_name:
                api.edit_user(email, name=ldap_name)
                logging.info(f"Changed name of {email} in Mailcow to {ldap_name}")
                unchanged = False

            if not api_custom_attr:
                api_custom_attr = {}

            if 'description' not in api_custom_attr:
                api_custom_attr['description'] = ''

            if config['LDAP_AVA_ATTR'] not in api_custom_attr:
                api_custom_attr[config['LDAP_AVA_ATTR']] = ''.encode()

            if api_custom_attr['description'] != ldap_description:
                logging.info(f"Changed description of {email} in Mailcow to {ldap_description}")
                unchanged = False
                changed_custom = True

            if api_custom_attr[config['LDAP_AVA_ATTR']] != ldap_avatar.decode("utf-8"):
                logging.info(f"Changed avatar of {email} in Mailcow.")
                unchanged = False
                changed_custom = True

            if changed_custom:
                api.edit_user(email, name=ldap_name, avatar=ldap_avatar, description=ldap_description)

            if unchanged:
                logging.info(f"Checked user {email}, unchanged")


    except Exception as e:
        logging.error(f"Error: {e}")
        # sys.exit(1)
        pass

    for email in filedb.get_unchecked_active_users():
        (api_user_exists, api_user_active, _, _) = api.check_user(email)

        if (api_user_active and api_user_active):
            api.edit_user(email, active=False)
            logging.info(f"Deactivated user {email} in Mailcow")

        filedb.user_set_active_to(email, False)
        logging.info(f"Deactivated user {email} in filedb")


def read_config():
    with open('config.ini', 'r') as config_file:
        return dict(
            map(lambda x: (x.split('=')[0], x.split('=')[1].strip()), config_file.readlines()))


def read_dovecot_passdb_conf_template():
    with open('templates/dovecot/ldap/passdb.conf', 'r') as template:
        return Template(template.read())


def read_dovecot_extra_conf():
    with open('templates/dovecot/extra.conf', 'r') as template:
        return Template(template.read())


def read_sogo_plist_ldap_template():
    with open('templates/sogo/plist_ldap', 'r') as template:
        return Template(template.read())


def apply_config(file_path, **kwargs):
    config_data = kwargs.get('config_data', None)
    if not config_data:
        return False

    with open(file_path, 'w') as config_file:
        config_file.write(config_data.substitute(**config))

    return True


if __name__ == '__main__':
    main()
