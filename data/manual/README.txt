把「用瀏覽器」從台灣彩券官網下載的年檔放到這個資料夾。

下載頁：
https://www.taiwanlottery.com/lotto/history/result_download/

建議：
1. 用 Chrome / Safari 開啟上面網址
2. 下載各年度 zip（例如 2024.zip、2023.zip…）
3. 把檔案直接丟進這個資料夾（data/manual/）
4. 執行：

   python3 scripts/test_crawl.py

或：

   python3 main.py

程式會優先讀這裡的本機檔，不需要再撞線上 WAF。
