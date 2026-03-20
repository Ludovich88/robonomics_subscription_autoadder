# Добавление устройств в RWS подписку Robonomics

Скрипт автоматически добавляет адреса устройств из файла в подписку RWS на Kusama Robonomics.

## Установка

```bash
pip install -r requirements.txt
```

## Подготовка

### 1. Ключ владельца подписки

**Вариант А: JSON из Polkadot{.js}** (рекомендуется)

Экспортируйте ключ из Polkadot{.js} (Account → Export) и укажите его при запуске:

```bash
python add_devices_to_rws.py --key-json 4DRWnRymeGcyXUwSyHY6ojuqLYhxqbMX7kKudeVVwhEefy4g.json --password "ваш_пароль"
```

Пароль можно задать переменной окружения `SUBSTRATE_KEY_PASSWORD` или скрипт запросит его интерактивно.

**Вариант Б: Мнемоника**

Создайте файл `key_mnemonic.txt` с мнемоникой (12 или 24 слова) аккаунта, который владеет подпиской RWS.

**Важно:** Файлы `*.json` и `key_mnemonic.txt` добавлены в `.gitignore`. Не публикуйте ключи.

Альтернатива: переменная окружения `SUBSTRATE_MNEMONIC`:
```bash
# Windows (CMD)
set "SUBSTRATE_MNEMONIC=word1 word2 ... word12"

# Windows (PowerShell)
$env:SUBSTRATE_MNEMONIC="word1 word2 ... word12"
```

### 2. Файл с адресами устройств

По умолчанию используется `robonomics_addresses.txt` в текущей папке. Каждый адрес — на отдельной строке. Строки с `#` игнорируются.

Можно указать путь к файлу из папки с конвейерной прошивкой:
```bash
python add_devices_to_rws.py --addresses-file ../robonomics_addresses.txt
```

## Использование

```bash
# С JSON-ключом Polkadot.js (приоритет над мнемоникой)
python add_devices_to_rws.py --key-json 4DRWnRymeGcyXUwSyHY6ojuqLYhxqbMX7kKudeVVwhEefy4g.json --password "пароль"
python add_devices_to_rws.py --key-json 4DRWnRymeGcyXUwSyHY6ojuqLYhxqbMX7kKudeVVwhEefy4g.json  # пароль запросит

# Добавить устройства (с мнемоникой из key_mnemonic.txt)
python add_devices_to_rws.py

# Указать путь к файлу с адресами
python add_devices_to_rws.py --addresses-file ../robonomics_addresses.txt

# Проверка без отправки транзакции
python add_devices_to_rws.py --dry-run

# Явно указать RPC (по умолчанию Kusama)
python add_devices_to_rws.py --rpc wss://kusama.rpc.robonomics.network/

# Для Polkadot (если потребуется)
python add_devices_to_rws.py --rpc wss://polkadot.rpc.robonomics.network/
```

## Процесс работы

1. Загрузка ключа владельца (JSON или мнемоника)
2. Подключение к `wss://kusama.rpc.robonomics.network/` (Kusama parachain Robonomics)
3. Запрос `rws.devices(owner)` — текущий список устройств
4. Чтение новых адресов из файла
5. Формирование списка: [владелец, ...существующие, ...новые]
6. Отправка транзакции `RWS.call(owner, RWS.set_devices(devices))`

## Автоматический запуск (Windows)

Скрипт `auto_add_device_to_rws.bat` устанавливает зависимости и запускает добавление устройств с JSON-ключом. Отредактируйте пароль в файле при необходимости.

## Интеграция с конвейером прошивки

После прошивки устройств скрипт `conveyor_flash_robonomics.py` сохраняет адреса в `robonomics_addresses.txt`. Скопируйте этот файл в папку `Robonomics_subscription` или укажите путь:

```bash
python add_devices_to_rws.py --addresses-file ../robonomics_addresses.txt
```
