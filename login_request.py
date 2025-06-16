import requests
import urllib.parse

# \ub85c\uadf8\uc778 \uc815\ubcf4 (\uc0ac\uc6a9\uc790 \uc81c\uacf5 \uac12)
USER_ID = '46513'
USER_PW = '1113'

# \ub85c\uadf8\uc778 API \uc5d4\ub4dc\ud3ec\uc778\ud2b8 URL
LOGIN_URL = 'https://store.bgfretail.com/websrc/deploy/loginProc.do'

# POST \uc694\uccad\uc5d0 \uc0ac\uc6a9\ud560 \ub370\uc774\ud130 \ud398\uc774\ub85c\ub4dc
login_data = {
    'userID': USER_ID,
    'userPW': USER_PW
}

# \ub370\uc774\ud130 \ud398\uc774\ub85c\ub4dc\ub97c URL \uc778\ucf54\ub529 \ud615\uc2dd\uc73c\ub85c \ubcc0\ud658 (application/x-www-form-urlencoded)
encoded_data = urllib.parse.urlencode(login_data)

# \uc694\uccad \ud5e4\ub354 \uc124\uc815
headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'Python Requests Client' # \uc694\uccad\uc744 \ubcf4\ub0b4\ub294 \ud074\ub77c\uc774\uc5b8\ud2b8 \uc2dd\ubcc4 (\uc120\ud0dd \uc0ac\ud56d)
}

print(f"\ub85c\uadf8\uc778 \uc2dc\ub3c4: {LOGIN_URL}")
print(f"\uc0ac\uc6a9\uc790 ID: {USER_ID}")

try:
    # POST \uc694\uccad \ubcf4\ub0b4\uae30
    response = requests.post(LOGIN_URL, data=encoded_data, headers=headers)

    # \uc751\ub2f5 \ud655\uc778
    print(f"\n\uc751\ub2f5 \uc0c1\ud0dc \ucf54\ub4dc: {response.status_code}")

    # \uc751\ub2f5 \ubd80\ubb38 \ucd9c\ub825 (\uc131\uacf5/\uc2e4\ud328 \uc815\ubcf4 \ud3ec\ud568 \uac00\ub2a5)
    # \uc11c\ubc84 \uc751\ub2f5 \ud615\uc2dd\uc5d0 \ub530\ub77c JSON \ub610\ub294 \uc77c\ubc18 \ud14d\uc2a4\ud2b8\ub85c \ud30c\uc2f1 \uac00\ub2a5
    try:
        response_json = response.json()
        print("\n\uc751\ub2f5 \ubd80\ubb38 (JSON):")
        import json
        print(json.dumps(response_json, indent=2))
    except requests.exceptions.JSONDecodeError:
        print("\n\uc751\ub2f5 \ubd80\ubb38 (\ud14d\uc2a4\ud2b8):")
        print(response.text)

    # \uc0c1\ud0dc \ucf54\ub4dc \ub610\ub294 \uc751\ub2f5 \ubd80\ubb38 \ub0b4\uc6a9\uc744 \uae30\ubc18\uc73c\ub85c \uc131\uacf5/\uc2e4\ud328 \ud310\ub2e8
    if response.status_code == 200: # \uc77c\ubc18\uc801\uc73c\ub85c 200 OK\ub294 \uc131\uacf5\uc744 \uc758\ubbf8
        # TODO: \uc11c\ubc84 \uc751\ub2f5 \ubd80\ubb38\uc758 \ub0b4\uc6a9(\uc608: \ud2b9\uc815 \uba54\uc2dc\uc9c0, \uc131\uacf5 \ucf54\ub4dc)\uc744 \ucd94\uac00\ub85c \ud655\uc778\ud574 \uc815\ud655\ud55c \ub85c\uadf8\uc778 \uc131\uacf5 \uc5ec\ubd80 \ud310\ub2e8 \ud544\uc694
        print("\n\ub85c\uadf8\uc778 \uc694\uccad \uc131\uacf5 (\uc0c1\ud0dc \ucf54\ub4dc 200 OK). \uc11c\ubc84 \uc751\ub2f5 \ubd80\ubb38\uc744 \ud655\uc778\ud558\uc138\uc694.")
    else:
        print(f"\n\ub85c\uadf8\uc778 \uc694\uccad \uc2e4\ud328. \uc0c1\ud0dc \ucf54\ub4dc: {response.status_code}")
        print("\uc11c\ubc84 \uc751\ub2f5 \ubd80\ubb38\uc744 \ud655\uc778\ud558\uc5ec \uc2e4\ud328 \uc6d0\uc778\uc744 \ud30c\uacac\ud558\uc138\uc694.")

except requests.exceptions.RequestException as e:
    print(f"\n\uc624\ub958 \ubc1c\uc0dd: {e}")
    print("\ub124\ud2b8\uc6cc\ud06c \uc5f0\uacb0 \ubb38\uc81c \ub610\ub294 URL \uc624\ub958\uc77c \uc218 \uc788\uc2b5\ub2c8\ub2e4.")
