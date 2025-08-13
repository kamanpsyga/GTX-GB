import os
import time
from playwright.sync_api import sync_playwright, Cookie

def login_to_panel(page, remember_web_cookie, login_email, login_password):
    """
    登录到 GTX Gaming 控制面板
    返回是否登录成功
    """
    # --- 尝试通过 REMEMBER_WEB_COOKIE 会话登录 ---
    if remember_web_cookie:
        print("尝试使用 REMEMBER_WEB_COOKIE 会话登录...")
        session_cookie = Cookie(
            name='remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d',
            value=remember_web_cookie,
            domain='.gtxgaming.co.uk',
            path='/',
            expires=time.time() + 3600 * 24 * 365,
            httpOnly=True,
            secure=True,
            sameSite='Lax'
        )
        page.context.add_cookies([session_cookie])
        
        # 测试登录状态，访问主页面
        test_url = "https://gamepanel2.gtxgaming.co.uk/home"
        print(f"正在测试登录状态，访问: {test_url}")
        page.goto(test_url, wait_until="networkidle", timeout=60000)

        # 检查是否成功登录
        if "login" in page.url or "auth" in page.url:
            print("使用 REMEMBER_WEB_COOKIE 登录失败或会话无效。将尝试使用邮箱密码登录。")
            page.context.clear_cookies()
            remember_web_cookie = None
        else:
            print("REMEMBER_WEB_COOKIE 登录成功。")
            return True

    # --- 如果 REMEMBER_WEB_COOKIE 不可用或失败，则回退到邮箱密码登录 ---
    if not remember_web_cookie:
        if not (login_email and login_password):
            print("错误: REMEMBER_WEB_COOKIE 无效，且未提供 LOGIN_EMAIL 或 LOGIN_PASSWORD。无法登录。")
            return False

        login_url = "https://gamepanel2.gtxgaming.co.uk/auth/login"
        print(f"正在访问登录页: {login_url}")
        page.goto(login_url, wait_until="networkidle", timeout=60000)

        # 登录表单元素选择器
        email_selector = 'input[name="email"]'
        password_selector = 'input[name="password"]'
        login_button_selector = 'button[type="submit"]'

        print("正在等待登录元素加载...")
        page.wait_for_selector(email_selector, timeout=30000)
        page.wait_for_selector(password_selector, timeout=30000)
        page.wait_for_selector(login_button_selector, timeout=30000)

        print("正在填充邮箱和密码...")
        page.fill(email_selector, login_email)
        page.fill(password_selector, login_password)

        print("正在点击登录按钮...")
        page.click(login_button_selector)

        # 等待登录完成，检查是否跳转到主页
        try:
            page.wait_for_url("**/home*", timeout=60000)
            print("邮箱密码登录成功。")
            return True
        except Exception:
            error_message_selector = '.alert.alert-danger, .error-message, .form-error'
            error_element = page.query_selector(error_message_selector)
            if error_element:
                error_text = error_element.inner_text().strip()
                print(f"邮箱密码登录失败: {error_text}")
                page.screenshot(path="login_fail_error_message.png")
            else:
                print("邮箱密码登录失败: 未能跳转到预期页面或检测到错误信息。")
                page.screenshot(path="login_fail_no_error.png")
            return False
    
    return False

def extend_server_time(page, server_url, server_name=""):
    """
    为指定服务器延长时间
    """
    try:
        server_display_name = server_name if server_name else server_url.split('/')[-1]
        print(f"\n=== 正在处理服务器: {server_display_name} ===")
        
        # 导航到服务器页面
        print(f"正在访问服务器页面: {server_url}")
        page.goto(server_url, wait_until="networkidle", timeout=60000)
        
        # 检查是否成功到达服务器页面
        if "login" in page.url or "auth" in page.url:
            print(f"访问服务器 {server_display_name} 失败，会话可能已过期。")
            return False
            
        # 查找并点击 "EXTEND 72 HOUR(S)" 按钮
        add_button_selector = 'button:has-text("EXTEND 72 HOUR(S)")'
        print(f"正在查找 'EXTEND 72 HOUR(S)' 按钮...")
        
        try:
            page.wait_for_selector(add_button_selector, state='visible', timeout=30000)
            page.click(add_button_selector)
            print(f"✅ 服务器 {server_display_name} 成功延长时间")
            time.sleep(3)  # 稍作等待
            return True
        except Exception as e:
            print(f"❌ 服务器 {server_display_name} 延长时间失败: 未找到按钮或点击失败 - {e}")
            page.screenshot(path=f"extend_button_not_found_{server_display_name}.png")
            return False
            
    except Exception as e:
        print(f"❌ 处理服务器 {server_display_name} 时发生错误: {e}")
        page.screenshot(path=f"server_error_{server_display_name}.png")
        return False

def add_server_time(server_configs=None):
    """
    批量为多个服务器延长时间
    server_configs: 服务器配置列表，每个配置包含 url 和可选的 name
    如果为空，则使用环境变量中的配置
    """
    # 获取环境变量
    remember_web_cookie = os.environ.get('REMEMBER_WEB_COOKIE')
    login_email = os.environ.get('LOGIN_EMAIL')
    login_password = os.environ.get('LOGIN_PASSWORD')

    # 检查是否提供了任何登录凭据
    if not (remember_web_cookie or (login_email and login_password)):
        print("错误: 缺少登录凭据。请设置 REMEMBER_WEB_COOKIE 或 LOGIN_EMAIL 和 LOGIN_PASSWORD 环境变量。")
        return False

    # 如果没有提供服务器配置，从环境变量中获取
    if server_configs is None:
        server_configs = get_server_configs_from_env()
    
    if not server_configs:
        print("错误: 没有找到任何服务器配置。")
        return False

    print(f"准备处理 {len(server_configs)} 个服务器")
    
    with sync_playwright() as p:
        # 在 GitHub Actions 中，通常使用 headless 模式
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 首先登录
            print("正在登录 GTX Gaming 控制面板...")
            if not login_to_panel(page, remember_web_cookie, login_email, login_password):
                print("登录失败，无法继续执行。")
                return False
            
            print("登录成功！开始处理服务器列表...")
            
            # 处理每个服务器
            success_count = 0
            total_count = len(server_configs)
            
            for config in server_configs:
                server_url = config.get('url', '')
                server_name = config.get('name', '')
                
                if not server_url:
                    print(f"跳过无效的服务器配置: {config}")
                    continue
                    
                if extend_server_time(page, server_url, server_name):
                    success_count += 1
                
                # 在处理下一个服务器前稍作等待
                time.sleep(2)
            
            print(f"\n=== 批量处理完成 ===")
            print(f"总计: {total_count} 个服务器")
            print(f"成功: {success_count} 个服务器")
            print(f"失败: {total_count - success_count} 个服务器")
            
            return success_count > 0

        except Exception as e:
            print(f"执行过程中发生未知错误: {e}")
            page.screenshot(path="general_error.png")
            return False
        finally:
            browser.close()

def get_server_configs_from_env():
    """
    从环境变量中获取服务器配置
    支持两种格式:
    1. SERVER_URLS: 逗号分隔的URL列表
    2. SERVER_LIST: JSON格式的服务器配置列表
    """
    import json
    
    # 方式1: 从 SERVER_LIST 环境变量读取 JSON 配置
    server_list_env = os.environ.get('SERVER_LIST')
    if server_list_env:
        try:
            server_configs = json.loads(server_list_env)
            print(f"从 SERVER_LIST 环境变量读取到 {len(server_configs)} 个服务器配置")
            return server_configs
        except json.JSONDecodeError as e:
            print(f"解析 SERVER_LIST JSON 格式失败: {e}")
    
    # 方式2: 从 SERVER_URLS 环境变量读取逗号分隔的URL列表
    server_urls_env = os.environ.get('SERVER_URLS')
    if server_urls_env:
        urls = [url.strip() for url in server_urls_env.split(',') if url.strip()]
        server_configs = []
        for i, url in enumerate(urls):
            server_configs.append({
                'url': url,
                'name': f'Server-{i+1}'
            })
        print(f"从 SERVER_URLS 环境变量读取到 {len(server_configs)} 个服务器URL")
        return server_configs
    
    # 方式3: 兼容旧版本，使用默认服务器
    default_url = "https://gamepanel2.gtxgaming.co.uk/server/fa13b794"
    print("未找到服务器配置环境变量，使用默认服务器")
    return [{'url': default_url, 'name': 'Default-Server'}]

if __name__ == "__main__":
    print("开始执行添加服务器时间任务...")
    success = add_server_time()
    if success:
        print("任务执行成功。")
        exit(0)
    else:
        print("任务执行失败。")
        exit(1)
