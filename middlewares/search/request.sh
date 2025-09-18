curl --request POST \
  --url http://12.244.66.225/ELLM.ELLM-OFFICE.V-1.0/querySources.do \
  --header 'Accept: */*' \
  --header 'Accept-Encoding: gzip, deflate, br' \
  --header 'Connection: keep-alive' \
  --header 'Content-Type: application/json' \
  --header 'User-Agent: PostmanRuntime-ApipostRuntime/1.1.0' \
  --header 'jumpCloud-Env: BASE' \
  --data '{
    "REQ_HEAD": {
        "TRANS_PROCESS": "",
        "TRAN_ID": ""
    },
    "REQ_BODY": {
        "param": {
            "messages": [
                {
                    "content": "规章制度",
                    "role": "user"
                }
            ],
            
            
            "repository": "okic-dynamicSearch",
            "param":{"channelId":"0"}
        },
        "muwpUser": {
            "muwp_branchID": "1000027159",
            "muwp_loginName": "xuew_4",
            "muwp_userCode": "9743616",
            "muwp_userName": "薛巍",
            "muwp_userID": "132298"
        }
    }
}'