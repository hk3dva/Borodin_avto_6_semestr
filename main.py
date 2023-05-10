import pdfplumber
import pandas as pd
import subprocess
import time
import os
import win32com.client


# перевод из pdf в df
def pdf_to_df(path):
    pages = []
    with pdfplumber.open(path) as pdf:
        for line in pdf.pages[1:]:
            for page in line.extract_tables():
                data = pd.DataFrame(page[1:], columns=page[0])
                pages.append(data.set_index(data.columns[0]))

    return pages


# получение параметров для варианта из страниц
def get_params(variant, pages):
    params = {}
    var = [int(el) for el in variant]
    for index, page in enumerate(pages):

        if index == 2 or index == 7 or index == 4:
            params[str(index + 1)] = page.iloc[var[index]].values
        else:
            params[str(index + 1)] = page.iloc[var[index] - 1].values

    return params


# Проверка номера на валидность
def varCheck(var):
    variant = [int(el) for el in var]
    if len(variant) != 9:
        return False
    if not (1 <= variant[0] <= 4):
        return False
    if not (1 <= variant[8] <= 6):
        return False
    if not (1 <= variant[1] <= 8) or not (1 <= variant[2] <= 8) or not (1 <= variant[4] <= 8) or not (
            1 <= variant[7] <= 8):
        return False
    if not (1 <= variant[3] <= 5) or not (1 <= variant[5] <= 5) or not (1 <= variant[6] <= 5):
        return False
    return True


def show_info(params, variant):
    print(f'номер варианта: A{variant}')
    for i in range(4):
        ip, mask = get_start_net_ip(params, i)
        print(f'Сеть {i+1}: ')
        print(f'Адрес сети: {ip}')
        print(f'Маска: {mask}')
        ip = [int(el) for el in ip.split('.')]
        ip[-1] += 1
        print(f'Адрес на интерфейсе fa1/0 маршрутизатора: {".".join([str(el) for el in ip])}')

        ip, mask = get_start_net_ip(params, i)
        ip = [int(el) for el in ip.split('.')]
        ip[-1] += 2
        print(f'Адрес на интерфейсе fa0/0 маршрутизатора: {".".join([str(el) for el in ip])}')
        print('')
    print('')

    for i in range(4):
        ip, mask = get_loopback_ip(params, i)
        print(f'Петлевой интерфейс r{i+1}')

        temp_ip = [el for el in ip.split('.')]
        temp_mask = [el for el in mask.split('.')]
        temp_ip[3] = int(temp_ip[-1]) & int(temp_mask[-1])

        print(f'Адрес сети: {".".join([str(el) for el in temp_ip])}')
        print(f'Маска: {mask}')
        print(f'Адрес данного петлевого интерфейса: {ip}')
        print('')


# маска, кол-во адресов
cods = {
    '/32': ['255.255.255.255', 1],
    '/31': ['255.255.255.254', 2],
    '/30': ['255.255.255.252', 4],
    '/29': ['255.255.255.248', 8],
    '/28': ['255.255.255.240', 16],
    '/27': ['255.255.255.224', 32],
    '/25': ['255.255.255.128', 128],
    '/24': ['255.255.255.0', 256],
    '/16': ['255.255.0.0', 65536]
}

files = [
    'r1.bat', 'r2.bat', 'r3.bat', 'r4.bat'
]


def leave(wsh):
    wsh.SendKeys('end{ENTER}')
    time.sleep(2)


def conf(wsh):
    wsh.SendKeys('configure terminal{ENTER}')
    time.sleep(2)


def temp_set(s):
    temp = s.split('/')
    temp[-1] = f'/{temp[-1]}'
    id = [temp[0].split('.')[el] for el in range(3)]
    id.append(0)
    return id, temp[-1]


# Возвращает ip адрес на lo а так же новую маску для него, в зависимости от номера маршрутизатора
def get_loopback_ip(params, num):
    r_num = int(files[num].split(".")[0][1]) - 1

    address_id_mask = params['6'][r_num]  # основной адрес и его маска
    ip, mask_len = temp_set(address_id_mask)

    address_num = params['5'][r_num]  # Номер в сети
    new_mask_len = cods[params['4'][r_num]]  # новая маска и длина одного сегмента сети

    address_name = params['3'][r_num]  # Какой id из диапазона брать, до /30 может быть после /30 должен быть отступ в 1

    if address_num == 'последняя':
        if new_mask_len[1] == 1:
            ip[-1] = cods[mask_len][1]
        else:
            ip[-1] = cods[mask_len][1] - new_mask_len[1]
        address_ip = ip
    else:
        address_ip = ip

    if address_name == 'последний':
        if new_mask_len[1] == 1:
            address_ip[-1] += new_mask_len[1]
        else:
            address_ip[-1] += new_mask_len[1] - 2
        address_ip = address_ip
    else:
        if new_mask_len[1] > 2:
            address_ip[-1] += 1
        address_ip = address_ip

    return '.'.join([str(el) for el in address_ip]), new_mask_len[0]


def get_start_net_ip(params, num):
    r_num = int(files[num].split(".")[0][1]) - 1
    ip, mask = temp_set(params['9'][r_num])
    mask_len = cods[mask]
    new_mask_len = cods[params['7'][r_num]]
    if params['8'][r_num] == 'последняя':
        ip[-1] = int(mask_len[1] / new_mask_len[1]) * (int(mask_len[1] / new_mask_len[1]) - 1)
    ip_res = ip
    return '.'.join([str(el) for el in ip_res]), new_mask_len[0]


def automatic_setting(params, variant):
    for num in range(4):
        commands = [
            f'cd RouterEdu/{files[num].split(".")[0]}',
            f'{files[num]}',
        ]
        subprocess.Popen('start cmd /k', shell=True)
        wsh = win32com.client.Dispatch('WScript.Shell')

        # Ожидаем, пока окно командной строки полностью загрузится
        while True:
            try:
                console = wsh.AppActivate('Командная строка')
                break
            except Exception as e:
                print('Ошибка открытия окна')

        time.sleep(2)
        # Вход
        time.sleep(2)
        wsh.SendKeys(commands[0] + '{ENTER}')
        time.sleep(2)
        wsh.SendKeys(commands[1] + '{ENTER}')
        time.sleep(10)
        wsh.SendKeys('{ENTER}')
        time.sleep(2)

        # Вход в привелегированный режим
        wsh.SendKeys('enable{ENTER}')
        time.sleep(2)

        # Запуск Шифрования паролей
        conf(wsh)
        wsh.SendKeys('service password-encryption{ENTER}')
        time.sleep(2)
        leave(wsh)

        # Использование AES
        conf(wsh)
        wsh.SendKeys('password encryption aes{ENTER}')
        time.sleep(2)
        leave(wsh)

        # Создание Пользователя (username=cisco password=cisco1 и тд.)
        conf(wsh)
        wsh.SendKeys('username cisco password cisco' + files[num].split(".")[0][1] + '{ENTER}')
        time.sleep(2)
        wsh.SendKeys('username admin privilege 15 secret admin{ENTER}')
        time.sleep(2)
        leave(wsh)

        # Создание пароля супер пользователя
        conf(wsh)
        wsh.SendKeys('enable password cisco{ENTER}')
        time.sleep(2)
        leave(wsh)

        # Присвоить имена маршрутизаторов (r1, r2, r3, r4)
        conf(wsh)
        wsh.SendKeys('hostname ' + files[num].split(".")[0] + '{ENTER}')
        time.sleep(2)
        leave(wsh)

        # Установить имя домена <вариант>.test.net
        conf(wsh)
        wsh.SendKeys('ip domain-name A' + variant + '.test.net{ENTER}')
        time.sleep(2)
        leave(wsh)

        # Поднять Shh
        conf(wsh)
        wsh.SendKeys('crypto key generate rsa{ENTER}')
        time.sleep(2)
        wsh.SendKeys('1024{ENTER}')
        time.sleep(2)

        leave(wsh)

        # Разрешить использовать только SSH
        conf(wsh)
        wsh.SendKeys('Line vty 0 4{ENTER}')
        time.sleep(2)
        wsh.SendKeys('Login local{ENTER}')
        time.sleep(2)
        wsh.SendKeys('transport input ssh{ENTER}')
        time.sleep(2)
        leave(wsh)

        # Использовать только версию 2 SSН.
        conf(wsh)
        wsh.SendKeys('ip ssh version 2{ENTER}')
        time.sleep(2)
        leave(wsh)

        # Журналирование всех событий SSH
        conf(wsh)
        wsh.SendKeys('ip ssh logging events{ENTER}')
        time.sleep(2)
        leave(wsh)

        # Журналирование всех попыток входа в маршрутизаторы с внешних IP - адресов.
        conf(wsh)
        wsh.SendKeys('Access-list 1 deny any log{ENTER}')   # deny
        time.sleep(2)

        # Доступ только из главного маршрутизатора
        if num != (int(params['1'][0][1]) - 1):
            ip, mask = get_start_net_ip(params, int(params['1'][0][1]) - 1)
            ip = [int(el) for el in ip.split('.')]
            ip[-1] += 1

            mask = mask.split('.')
            mask[0] = 255 - int(mask[0])
            mask[1] = 255 - int(mask[1])
            mask[2] = 255 - int(mask[2])
            mask[3] = 255 - int(mask[3])
            wsh.SendKeys('access-list 1 permit ' + '.'.join([str(el) for el in ip]) + ' ' + '.'.join([str(el) for el in mask]) + ' log{ENTER}')
            time.sleep(2)

        wsh.SendKeys('line vty 0 4{ENTER}')
        time.sleep(2)
        wsh.SendKeys('access-class 1 in{ENTER}')
        time.sleep(2)

        leave(wsh)

        # Loopback
        ip, mask = get_loopback_ip(params, num)

        conf(wsh)
        wsh.SendKeys('interface loopback ' + params['2'][num] + '{ENTER}')
        time.sleep(2)
        wsh.SendKeys('ip address ' + ip + ' ' + mask + '{ENTER}')
        time.sleep(2)
        leave(wsh)

        # Настройка кольцевой очереди между маршрутизаторами
        # fa1/0
        ip, mask = get_start_net_ip(params, num)
        ip = [int(el) for el in ip.split('.')]
        ip[-1] += 1

        conf(wsh)
        wsh.SendKeys('interface fa1/0{ENTER}')
        time.sleep(2)

        wsh.SendKeys('ip address ' + '.'.join([str(el) for el in ip]) + ' ' + mask + '{ENTER}')
        time.sleep(2)
        wsh.SendKeys('No shu {ENTER}')
        time.sleep(2)
        wsh.SendKeys('Duple full{ENTER}')
        leave(wsh)

        # fa0/0
        ip, mask = get_start_net_ip(params, num - 1)
        ip = [int(el) for el in ip.split('.')]
        ip[-1] += 2
        conf(wsh)
        wsh.SendKeys('interface fa0/0{ENTER}')
        time.sleep(2)
        wsh.SendKeys('ip address ' + '.'.join([str(el) for el in ip]) + ' ' + mask + '{ENTER}')
        time.sleep(2)
        wsh.SendKeys('No shu {ENTER}')
        time.sleep(2)
        wsh.SendKeys('Duple full{ENTER}')
        leave(wsh)

        # Статическая маршрутизация
        conf(wsh)
        for i in range(0, 4):
            ip, mask = get_loopback_ip(params, i)
            if i == num:
                continue
            if i < num:
                ip_1, mask_1 = get_start_net_ip(params, num - 1)
                ip_1 = [int(el) for el in ip_1.split('.')]
                ip_1[-1] += 1
            else:
                ip_1, mask_1 = get_start_net_ip(params, num)
                ip_1 = [int(el) for el in ip_1.split('.')]
                ip_1[-1] += 2
            wsh.SendKeys('ip route ' + ip + ' ' + mask + ' ' + '.'.join([str(el) for el in ip_1]) + '{ENTER}')
            time.sleep(2)

        for i in range(0, 4):
            if i == num - 1 and num == i:
                continue
            ip, mask = get_start_net_ip(params, i)
            ip_1, mask_1 = get_start_net_ip(params, num)
            wsh.SendKeys('ip route ' + ip + ' ' + mask + ' ' + ip_1 + '{ENTER}')
            time.sleep(2)
        leave(wsh)

        # сохранение результата
        wsh.SendKeys('write{ENTER}')


def generate(variant):
    if not varCheck(variant):
        print('Номер варианта указан не корректно')
        return 1

    pages = pdf_to_df('variant.pdf')
    params = get_params(variant, pages)
    automatic_setting(params, variant)
    print(f'Информация для заполнения отчета')
    show_info(params, variant)
    return 0


if __name__ == '__main__':
    generate('151111321')
