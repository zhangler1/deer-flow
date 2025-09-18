curl --request POST \
  --url http://localhost:8000/ELLM.ELLM-OFFICE.V-1.0/querySources.do \
  --header 'Accept: */*' \
  --header 'Accept-Encoding: gzip, deflate, br' \
  --header 'Connection: keep-alive' \
  --header 'Content-Type: application/json' \
  --header 'User-Agent: PostmanRuntime-ApipostRuntime/1.1.0' \
  --header 'jumpCloud-Env: BASE' \
  --data '{\n    "REQ_HEAD": {\n        "TRANS_PROCESS": "",\n        "TRAN_ID": ""\n    },\n    "REQ_BODY": {\n        "param": {\n            "messages": [\n                {\n                    "content": "规章制度",\n                    "role": "user"\n                }\n            ],\n            "repository": "okic-dynamicSearch",\n            "param":{"channelId":"0"}\n        },\n        "muwpUser": {\n            "muwp_branchID": "1000027159",\n            "muwp_loginName": "xuew_4",\n            "muwp_userCode": "9743616",\n            "muwp_userName": "薛巍",\n            "muwp_userID": "132298"\n        }\n    }\n}'