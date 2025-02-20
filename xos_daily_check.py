import asyncio
from datetime import datetime
import sys

import cloudscraper
import httpx
from loguru import logger

logger.remove()
logger.add(sys.stdout, format='<g>{time:YYYY-MM-DD HH:mm:ss:SSS}</g> | <c>{level}</c> | <level>{message}</level>')


class ScraperReq:
    def __init__(self, proxy: dict, header: dict):
        self.scraper = cloudscraper.create_scraper(browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False,
        })
        self.proxy: dict = proxy
        self.header: dict = header

    def post_req(self, url, req_json, req_param):
        # logger.info(self.header)
        # logger.info(req_json)
        return self.scraper.post(url=url, headers=self.header, json=req_json, proxies=self.proxy, params=req_param)

    async def post_async(self, url, req_param=None, req_json=None):
        return await asyncio.to_thread(self.post_req, url, req_json, req_param)

    def get_req(self, url, req_param):
        return self.scraper.get(url=url, headers=self.header, params=req_param, proxies=self.proxy)

    async def get_async(self, url, req_param=None, req_json=None):
        return await asyncio.to_thread(self.get_req, url, req_param)


class XOS:
    def __init__(self, headers: dict, proxy: str, index: int, mnemonic: str, JS_SERVER: str = '127.0.0.1'):
        self.sol_address = None
        self.sol_me_address = None
        self.proxy = proxy
        self.index = index
        proxy_dict = {
            'http': proxy,
            'https': proxy,
        }
        self.scrape = ScraperReq(proxy_dict, headers)
        self.JS_SERVER = f'http://{JS_SERVER}:3666'
        self.mnemonic = mnemonic
        self.wallet_address = None

    async def check_proxy(self):
        res = await self.scrape.get_async(f'http://ip-api.com/json')
        print(res.text)
        return True

    async def get_wallet_address(self):
        for i in range(3):
            try:
                res = await httpx.AsyncClient(timeout=30).post(f'{self.JS_SERVER}/api/wallet_address',
                                                               json={'mnemonic': self.mnemonic})
                print(res.text)
                if res.json()['success']:
                    self.wallet_address = res.json()['data']['address']
                    logger.info(f'{self.index}, {self.proxy} {self.wallet_address} 获取钱包成功')
                    return True
                else:
                    logger.error(f'{self.index}, {self.proxy} 获取钱包失败')
                    continue
            except Exception as e:
                logger.error(f'{self.index}, {self.proxy} get_wallet_address error: {e}')
                await asyncio.sleep(3)
                continue

    async def get_sign_message(self):
        for i in range(3):
            try:
                res = await self.scrape.get_async(
                    f'https://api.x.ink/v1/get-sign-message2?walletAddress={self.wallet_address}')
                message = res.json()['message']
                logger.info(f'{self.index}, {self.proxy} {self.wallet_address} 获取签名消息成功: {message}')
                # 获取签名
                sign_payload = {
                    'mnemonic': self.mnemonic,
                    'proxy': self.proxy,
                    'payload': message
                }

                sign_res = await httpx.AsyncClient().post(f'{self.JS_SERVER}/api/sign', json=sign_payload)
                if sign_res.json()['success']:
                    signature = sign_res.json()['signature']
                    logger.info(f'{self.index}, {self.proxy} {self.wallet_address} 获取签名成功: {signature}')
                    # 验证登录
                    verify_payload = {
                        "walletAddress": self.wallet_address,
                        "signMessage": message,
                        "signature": signature,
                        "referrer": None
                    }

                    verify_res = await self.scrape.post_async(
                        'https://api.x.ink/v1/verify-signature2',
                        req_json=verify_payload
                    )

                    if verify_res.json()['success']:
                        token = verify_res.json()['token']
                        logger.info(f'{self.index}, {self.proxy} {self.wallet_address} 验证登录成功: {token}')
                        # Update authorization header with the token
                        self.scrape.header['authorization'] = f'Bearer {token}'
                        return True
                    else:
                        logger.error(
                            f'{self.index}, {self.proxy} {self.wallet_address} 验证登录失败: {verify_res.text}')
                        continue


                else:
                    logger.error(f'{self.index}, {self.proxy} {self.wallet_address} 获取签名失败: {sign_res.text}')
                    continue



            except Exception as e:
                logger.error(f'{self.index}, {self.proxy} {self.wallet_address} 获取签名消息失败: {e}')
                await asyncio.sleep(3)
                continue
        return False

    async def daily_task(self):
        try:
            # Get user info
            res = await self.scrape.get_async('https://api.x.ink/v1/me')
            user_info = res.json()['data']
            # Print relevant user info
            logger.info(f"{self.index}, {self.proxy} {self.wallet_address} Points: {user_info['points']}, "
                        f"Check-ins: {user_info['check_in_count']}, "
                        f"SOL Address: {user_info['sol']}")
            self.sol_me_address = user_info['sol']

            # Check if already checked in today
            if user_info['lastCheckIn'] is not None:
                last_check_in = datetime.strptime(user_info['lastCheckIn'], '%Y-%m-%dT%H:%M:%S.%fZ')
                now = datetime.utcnow()
                if last_check_in.date() == now.date():
                    logger.info(f'{self.index}, {self.proxy} {self.wallet_address} 今日已签到')
                    return True
            # Submit check-in
            check_in_res = await self.scrape.post_async(
                'https://api.x.ink/v1/check-in',
                req_json={}
            )

            if check_in_res.json()['success']:
                logger.info(
                    f'{self.index}, {self.proxy} {self.wallet_address} 签到成功，获得 {check_in_res.json()["pointsEarned"]} 积分，已签到 {check_in_res.json()["check_in_count"]} 天')
                return True
            else:
                logger.error(f'{self.index}, {self.proxy} {self.wallet_address} 签到失败: {check_in_res.text}')
                return False

        except Exception as e:
            logger.error(f'{self.index}, {self.proxy} {self.wallet_address} 签到过程出错: {e}')
            return False

    async def bind_sol(self):
        try:
            # Get sign message for SOL binding
            # Get SOL wallet address from mnemonic
            for i in range(3):
                try:
                    payload = {
                        'mnemonic': self.mnemonic
                    }
                    res = await httpx.AsyncClient(timeout=30).post(
                        f'{self.JS_SERVER}/api/solana/wallet_address',
                        json=payload)
                    if res.json()['success']:
                        self.sol_address = res.json()['data']['address']
                        logger.info(f'{self.index}, {self.proxy} 获取SOL钱包地址成功: {self.sol_address}')
                        break
                    else:
                        logger.error(f'{self.index}, {self.proxy} 获取SOL钱包地址失败: {res.text}')
                except Exception as e:
                    logger.error(f'{self.index}, {self.proxy} 获取SOL钱包地址失败: {e}')
                    await asyncio.sleep(1)
                    if i == 2:
                        return False
            sign_msg_url = f'https://api.x.ink/v1/get-solana-sign-message'
            params = {'solanaAddress': self.sol_address}
            sign_msg_res = await self.scrape.get_async(sign_msg_url, params)

            if not sign_msg_res.json()['success']:
                logger.error(
                    f'{self.index}, {self.proxy} {self.wallet_address} 获取SOL签名消息失败: {sign_msg_res.text}')
                return False

            message = sign_msg_res.json()['message']
            logger.info(f'{self.index}, {self.proxy} {self.wallet_address} 获取SOL签名消息成功: {message}')

            # Get signature
            sign_payload = {
                'mnemonic': self.mnemonic,
                'payload': message,
                'proxy': self.proxy
            }

            sign_res = await httpx.AsyncClient().post(f'{self.JS_SERVER}/api/sign', json=sign_payload)

            if not sign_res.json()['success']:
                logger.error(f'{self.index}, {self.proxy} {self.wallet_address} 获取SOL签名失败: {sign_res.text}')
                return False

            signature = sign_res.json()['signature']
            logger.info(f'{self.index}, {self.proxy} {self.wallet_address} 获取SOL签名成功: {signature}')

            # Bind SOL address
            bind_payload = {
                'solanaAddress': self.sol_address,
                'signature': signature,
                'message': message
            }

            bind_res = await self.scrape.post_async('https://api.x.ink/v1/bind-solana', req_json=bind_payload)

            if bind_res.json()['success']:
                logger.info(f'{self.index}, {self.proxy} {self.wallet_address} 绑定SOL地址成功: {self.sol_address}')
                return True
            else:
                logger.error(f'{self.index}, {self.proxy} {self.wallet_address} 绑定SOL地址失败: {bind_res.text}')
                return False

        except Exception as e:
            logger.error(f'{self.index}, {self.proxy} {self.wallet_address} 绑定SOL地址过程出错: {e}')
            return False

    async def loop_task(self):
        await self.check_proxy()
        while True:
            try:
                await self.get_wallet_address()
                await self.get_sign_message()
                await self.daily_task()
                if self.sol_me_address is None:
                    await self.bind_sol()
                await asyncio.sleep(8 * 3600)
            except Exception as e:
                logger.error(f'{self.index}, {self.proxy} {self.wallet_address} 执行出错: {e}')
                await asyncio.sleep(4 * 3600)


async def run(acc: dict, index: int, JS_SERVER: str):
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.6',
        'origin': 'https://x.ink',
        'referer': 'https://x.ink/',
    }

    xos = XOS(
        headers=headers,
        proxy=acc['proxy'],
        mnemonic=acc['mnemonic'],
        index=index,
        JS_SERVER=JS_SERVER
    )
    await xos.loop_task()


async def main(JS_SERVER: str):
    accs = []
    with open('./acc', 'r', encoding='utf-8') as file:
        for line in file.readlines():
            parts = line.strip().split('----')
            mnemonic = parts[0]
            proxy = parts[1]
            accs.append({'mnemonic': mnemonic, 'proxy': proxy})

    tasks = []
    for index, acc in enumerate(accs):
        tasks.append(run(acc, index, JS_SERVER))

    await asyncio.gather(*tasks)


if __name__ == '__main__':
    logger.info('🚀 [ILSH] XOS DAILY CHECK v1.0 | Airdrop Campaign Live')
    logger.info('🌐 ILSH Community: t.me/ilsh_auto')
    logger.info('🐦 X(Twitter): https://x.com/hashlmBrian')
    logger.info('☕ Pay meCoffe：USDT（TRC20）:TAiGnbo2isJYvPmNuJ4t5kAyvZPvAmBLch')

    JS_SERVER = '127.0.0.1'

    print('----' * 30)
    print('请验证, JS_SERVER的host是否正确')
    print('pay attention to whether the host of the js service is correct')
    print('----' * 30)
    asyncio.run(main(JS_SERVER))
