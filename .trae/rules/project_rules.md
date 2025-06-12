这个项目包含了几个微服务：
1、fetcher: 数据抓取服务
2、admin: 后台管理服务
3、admin-ui: 后台管理界面
4、demo: 演示服务

docker目录结构:
1、docker/environments/dev开发环境
2、docker/environments/prod生产环境

项目技术栈:
1、fetcher: python + fastapi + celery
2、admin: golang + kratos
3、admin-ui: nextjs + antdesign
4、demo: nextjs + antdesign