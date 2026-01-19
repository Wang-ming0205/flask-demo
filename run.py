from app import create_app
from app.services.upload_service import init_upload_folders  # ← 引入初始化函式

app = create_app()

with app.app_context():
    init_upload_folders()
    print(app.url_map)

if __name__ == "__main__":
    app.run()#debug=True)#關一下
