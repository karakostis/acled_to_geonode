import requests
import json
import optparse
import logging

from datetime import datetime

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36"


def create_session(config):
    session_params = config.get("config").copy()

    session = requests.session()

    host = session_params.pop("host")
    login_url = "{host}/account/login/".format(host=host)

    headers = {"User-Agent": USER_AGENT, "Referer": login_url}

    try:
        session.get(login_url)
    except:
        raise_error("Could not connect to server.")

    # Udpate params.
    session_params["csrfmiddlewaretoken"] = session.cookies["csrftoken"]

    response = session.post(login_url, data=session_params, headers=headers)
    if "sessionid" not in session.cookies:
        raise_error("Missing session id in response")

    return session


def raise_error(info):
    logging.error(info)
    exit(1)


def check_field(key, params):
    value = params.get(key)
    if value is None:
        raise_error("Missing configuration parameter: {}".format(key))


def validate(config):
    # Validate mandatory params.
    server_config = config["config"]
    keys = ["host", "username", "password"]
    [check_field(k, server_config) for k in keys]

    files = config["files"]
    keys = ["path", "name"]
    for f in files:
        [check_field(k, f) for k in keys]


def upload(layers, config, session):
    session_params = config.get("config").copy()

    host = session_params.pop("host")
    upload_url = "{host}/layers/upload".format(host=host)
    headers = {"User-Agent": USER_AGENT, "Referer": upload_url}
    for f in config.get("files"):
        name = f.get("name")

        filtered = [l for l in layers if l["title"] == name]

        if len(filtered) == 1:
            layer = filtered[0]
            url = "{host}{detail}/remove".format(host=host, detail=layer["detail_url"])
            msg = "Deleting layer {name}".format(name=name)

            logging.info(msg)

            payload = {
                "csrfmiddlewaretoken": session.cookies["csrftoken"],
                "value": layer["detail_url"].split("/", 2)[-1],
            }

            resp = session.post(url, data=payload, headers=headers)
            print(resp)

        if len(filtered) > 1:
            raise_error("Repeated layer name")

        url = upload_url
        msg = "Uploading layer {name}".format(name=name)

        logging.info(msg)

        try:
            session.get(url, headers=headers)
        except:
            raise_error("Could not connect to server.")

        files = {"base_file": (f.get("name"), open(f.get("path"), "rb"))}
        payload = {
            "name": name,
            "source": f.get("source"),
            "date": datetime.now().isoformat(),
            "csrfmiddlewaretoken": session.cookies["csrftoken"],
            "permissions": '{"users":{"AnonymousUser":["view_resourcebase", "download_resourcebase"]},"groups":{}}',
            "charset": "UTF-8",
        }

        resp = session.post(url, files=files, data=payload, headers=headers)
        print(resp)


def get_layers(config, session):
    session_params = config.get("config").copy()

    host = session_params.pop("host")
    username = config.get("config").get("username")

    layers_url = "{host}/api/layers/?owner__username={username}".format(
        host=host, username=username
    )

    headers = {"User-Agent": USER_AGENT, "Referer": layers_url}

    try:
        resp = session.get(layers_url, headers=headers)
    except:
        raise_error("Could not connect to server.")

    if resp.status_code != 200:
        raise_error("Invalid response from server")

    data = resp.json()
    layers = data["objects"]

    logging.info(
        "Found {count} layers for user {username}".format(
            count=len(layers), username=username
        )
    )

    return layers


def main():
    parser = optparse.OptionParser()
    parser.add_option("-c", "--config", dest="config")
    options, _ = parser.parse_args()

    if options.config is None:
        raise_error("No configuration file provided")

    # Open config file.
    try:
        with open(options.config) as f:
            config = json.load(f)
    except json.decoder.JSONDecodeError:
        raise_error("Invalid json file")

    validate(config)
    logging.info("Successfull file validation")

    session = create_session(config)
    layers = get_layers(config, session)
    upload(layers, config, session)


if __name__ == "__main__":
    main()
