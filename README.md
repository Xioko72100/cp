# cp_final_ex

## 🚀 Waitress 啟動步驟 (Windows 環境)

### 步驟一：安裝 Waitress

請確保您已經在虛擬環境中，並安裝 Waitress 套件。

```bash
# 確保您已經啟用虛擬環境 (venv\Scripts\activate)

# 安裝 Waitress
pip install waitress
```

### 步驟二：建立啟動腳本 (`run_waitress.py`)

為了讓 Waitress 知道如何啟動您的 Flask 應用程式 (`app.py` 中的 `app` 物件)，我們需要建立一個單獨的 Python 腳本，例如命名為 `run_waitress.py`。

在您的專案根目錄下建立此檔案，內容如下：

```python
# run_waitress.py

from waitress import serve
from app import app  # 從您的 app.py 檔案中導入 Flask 應用程式實例

# 設定伺服器監聽的位址和埠號
HOST = '0.0.0.0'  # 監聽所有 IPv4 接口
PORT = 5000

print(f"Waitress 伺服器啟動中，監聽於 http://{HOST}:{PORT}")
serve(app, host=HOST, port=PORT)
```

### 步驟三：啟動伺服器 (IPv4 預設)

在命令提示字元或 PowerShell 中執行您剛建立的啟動腳本。

```bash
# 確保您已經在 (venv) 虛擬環境中

# 執行 Waitress 腳本
python run_waitress.py
```

伺服器將會啟動，並在您指定的埠號上監聽來自所有 IPv4 位址的連線。

-----

## 🌐 使用 IPv6 位址的啟動方式

如果您的電腦有一個**外部 IPv6 位址**，並且您希望 Waitress 能夠透過該 IPv6 位址提供服務，您需要在 `run_waitress.py` 中進行以下修改：

### 步驟一：修改啟動腳本 (`run_waitress.py`)

您需要將 `HOST` 變數設定為監聽所有 IPv6 接口的專用位址 **`::`** (IPv6 的不確定位址，相當於 IPv4 的 `0.0.0.0`)。

```python
# run_waitress.py (IPv6 版本)

from waitress import serve
from app import app

# 設定為監聽所有 IPv6 接口 (::)
HOST = '::' 
PORT = 5000

print(f"Waitress 伺服器啟動中，監聽於 http://[{HOST}]:{PORT} (IPv6)")
serve(app, host=HOST, port=PORT)
```

### 步驟二：啟動伺服器 (IPv6)

執行修改後的腳本：

```bash
# 執行 Waitress 腳本
python run_waitress.py
```

### 💡 存取提示 (使用 IPv6)

當您使用 IPv6 位址啟動伺服器時，**瀏覽器存取時必須將 IPv6 位址用方括號 `[]` 括起來**，以區分位址和埠號。

  * **內部測試存取：** `http://[::1]:5000` (如果伺服器監聽 `::`，並使用本機 IPv6 迴路位址)
  * **外部存取：** 如果您的外部 IPv6 位址是 `2001:db8::1234`，則使用者應存取：`http://[2001:db8::1234]:5000`

> **重要提醒：** 如果您使用 `HOST = '::'` 啟動，Waitress 通常會同時監聽 IPv4 和 IPv6 接口，這稱為**雙堆疊 (Dual Stack)** 模式，是推薦的設定。