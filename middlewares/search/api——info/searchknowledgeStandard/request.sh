curl --request POST \
  --url http://euvd-chn-slb-7002.bocomm.com/EUVD.EUVD-ADAPTER.V-1.0/searchKnowledgeStandard.do \
  --header 'Accept: */*' \
  --header 'Accept-Encoding: gzip, deflate, br' \
  --header 'Connection: keep-alive' \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --header 'User-Agent: PostmanRuntime-ApipostRuntime/1.1.0' \
  --data 'REQ_MESSAGE={     "REQ_HEAD": {},     "REQ_BODY": {         "param": {             "keyword": "安徽省半导体产业政策 2026",             "caller": "P2024146",             "userCode": "9855835",             "searchType": "2",             "qaType": [                 1          ],             "domainTagList": [],             "spaceCodeList": [                 "SP0999999"             ],      "customizedTagList": [],             "vectorTopN":3,         "textTopN":0,    "model": 0,             "attachFlag": 1,             "threshold": 0.1,             "publishedFlag": 0,             "latestFlag": null,             "delFlag": 0         }     } }'