#!/usr/bin/env python3
"""
Добавление адресов устройств из robonomics_addresses.txt в подписку RWS на Kusama Robonomics.

Использование:
  # Ключ из Polkadot.js JSON (экспорт из Polkadot{.js}):
  python add_devices_to_rws.py --key-json 4DRWnRymeGcyXUwSyHY6ojuqLYhxqbMX7kKudeVVwhEefy4g.json --password "ваш_пароль"
  python add_devices_to_rws.py --key-json 4DRWnRymeGcyXUwSyHY6ojuqLYhxqbMX7kKudeVVwhEefy4g.json  # пароль запросит интерактивно

  # Ключ из мнемоники:
  python add_devices_to_rws.py --mnemonic-file key_mnemonic.txt
  python add_devices_to_rws.py --mnemonic-file key_mnemonic.txt --addresses-file ../robonomics_addresses.txt
  python add_devices_to_rws.py --mnemonic-file key_mnemonic.txt --dry-run  # без отправки транзакции

Пароль для JSON: переменная окружения SUBSTRATE_KEY_PASSWORD или --password.
"""
import argparse
import os
import sys
from pathlib import Path

# Конфигурация по умолчанию (Kusama parachain Robonomics)
DEFAULT_RPC = "wss://kusama.rpc.robonomics.network/"
DEFAULT_ADDRESSES_FILE = "robonomics_addresses.txt"
DEFAULT_MNEMONIC_FILE = "key_mnemonic.txt"


def load_mnemonic(path: str) -> str:
    """Загрузка мнемоники из файла (одна строка, 12 или 24 слова)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Файл с мнемоникой не найден: {path}")
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    raise ValueError("Файл с мнемоникой пуст или содержит только комментарии")


def load_addresses_from_file(path: str) -> list[str]:
    """Загрузка адресов из файла (по одному на строку, пустые и # игнорируются)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Файл с адресами не найден: {path}")
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    addresses = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            addresses.append(line)
    return addresses


def normalize_address(addr: str) -> str:
    """Нормализация SS58 адреса (убираем лишние пробелы)."""
    return addr.strip()


def main():
    parser = argparse.ArgumentParser(
        description="Добавление устройств в RWS подписку Robonomics (Kusama)"
    )
    parser.add_argument(
        "--key-json",
        default=None,
        help="Путь к JSON-ключу Polkadot.js (экспорт из Polkadot{.js}). Приоритет над мнемоникой.",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Пароль для расшифровки JSON-ключа (или SUBSTRATE_KEY_PASSWORD)",
    )
    parser.add_argument(
        "--mnemonic-file",
        default=DEFAULT_MNEMONIC_FILE,
        help=f"Путь к файлу с мнемоникой владельца подписки (по умолчанию: {DEFAULT_MNEMONIC_FILE})",
    )
    parser.add_argument(
        "--addresses-file",
        default=DEFAULT_ADDRESSES_FILE,
        help=f"Файл с новыми адресами (по умолчанию: {DEFAULT_ADDRESSES_FILE})",
    )
    parser.add_argument(
        "--rpc",
        default=DEFAULT_RPC,
        help=f"WebSocket RPC Robonomics (по умолчанию: Kusama parachain)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только проверить, не отправлять транзакцию",
    )
    parser.add_argument(
        "--owner",
        default=None,
        help="Адрес владельца подписки (если не указан — будет определён из мнемоники)",
    )
    args = parser.parse_args()

    # Загрузка ключа (JSON из Polkadot.js или мнемоника)
    keypair = None
    owner_address = args.owner

    if args.key_json:
        key_json_path = Path(args.key_json)
        if not key_json_path.exists():
            print(f"Ошибка: JSON-файл ключа не найден: {args.key_json}")
            sys.exit(1)
        json_data = key_json_path.read_text(encoding="utf-8")
        password = args.password or os.environ.get("SUBSTRATE_KEY_PASSWORD")
        if not password:
            try:
                import getpass
                password = getpass.getpass("Пароль для JSON-ключа: ")
            except (ImportError, EOFError):
                print("Ошибка: укажите пароль через --password или SUBSTRATE_KEY_PASSWORD")
                sys.exit(1)
        try:
            # Polkadot.js может экспортировать с высокими scrypt N/r/p — увеличиваем maxmem
            import nacl.hashlib as _nacl_hl
            _orig_scrypt = _nacl_hl.scrypt
            def _scrypt_high_mem(password, salt, *, n, r, p, dklen=32, maxmem=2**26, **kw):
                return _orig_scrypt(password, salt, n=n, r=r, p=p, dklen=dklen, maxmem=max(maxmem, 2**30), **kw)
            _nacl_hl.scrypt = _scrypt_high_mem
            from substrateinterface import Keypair
            keypair = Keypair.create_from_encrypted_json(json_data, passphrase=password, ss58_format=32)
            owner_address = owner_address or keypair.ss58_address
        except Exception as e:
            print(f"Ошибка расшифровки JSON-ключа: {e}")
            print("Проверьте пароль и формат файла (Polkadot.js export).")
            sys.exit(1)
    else:
        mnemonic = os.environ.get("SUBSTRATE_MNEMONIC")
        if not mnemonic:
            try:
                mnemonic = load_mnemonic(args.mnemonic_file)
            except (FileNotFoundError, ValueError) as e:
                print(f"Ошибка: {e}")
                print("\nИспользуйте --key-json <путь> для Polkadot.js JSON или создайте key_mnemonic.txt.")
                print("Или задайте переменную окружения SUBSTRATE_MNEMONIC.")
                sys.exit(1)
        # keypair создадим позже после импорта SubstrateInterface

    # Загрузка новых адресов
    try:
        new_addresses = [normalize_address(a) for a in load_addresses_from_file(args.addresses_file)]
    except FileNotFoundError as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

    if not new_addresses:
        print(f"В файле {args.addresses_file} нет адресов для добавления.")
        sys.exit(0)

    print(f"[*] Загружено {len(new_addresses)} адресов из {args.addresses_file}")

    try:
        from substrateinterface import SubstrateInterface, Keypair
    except ImportError:
        print("Ошибка: установите substrate-interface: pip install substrate-interface")
        sys.exit(1)

    # Подключение к ноде
    print(f"[*] Подключение к {args.rpc}...")
    try:
        substrate = SubstrateInterface(url=args.rpc)
    except Exception as e:
        print(f"Ошибка подключения к RPC: {e}")
        sys.exit(1)

    # Ключ владельца (если ещё не загружен из JSON)
    if keypair is None:
        try:
            keypair = Keypair.create_from_mnemonic(mnemonic, ss58_format=32)
        except Exception as e:
            print(f"Ошибка создания ключа из мнемоники: {e}")
            sys.exit(1)
        owner_address = args.owner or keypair.ss58_address
    print(f"[*] Владелец подписки: {owner_address}")

    # Запрос текущих устройств из rws.devices(owner)
    # Robonomics Polkadot: паллет называется RWS (все заглавные)
    print("[*] Запрос текущего списка устройств (rws.devices)...")
    result = None
    for pallet in ("RWS", "Rws", "rws"):
        try:
            result = substrate.query(pallet, "Devices", [owner_address])
            break
        except Exception:
            continue
    if result is None:
        print("Ошибка: паллет Rws/rws или storage Devices не найден в runtime.")
        print("Проверьте RPC (Kusama: wss://kusama.rpc.robonomics.network/ или Polkadot: wss://polkadot.rpc.robonomics.network/)")
        sys.exit(1)

    existing = []
    if result.value is not None:
        raw = result.value
        if isinstance(raw, (list, tuple)):
            for a in raw:
                s = str(getattr(a, "value", a))
                if s and s != "None":
                    existing.append(normalize_address(s))
        elif hasattr(raw, "__iter__") and not isinstance(raw, (str, bytes)):
            for a in raw:
                s = str(getattr(a, "value", a))
                if s and s != "None":
                    existing.append(normalize_address(s))

    existing = [a for a in existing if a]
    print(f"[*] Текущих устройств в подписке: {len(existing)}")

    # Фильтрация: только новые адреса
    existing_set = {a for a in existing}
    to_add = [a for a in new_addresses if a not in existing_set]

    if not to_add:
        print("[*] Все адреса из файла уже есть в подписке. Ничего делать не нужно.")
        sys.exit(0)

    print(f"[*] Новых адресов для добавления: {len(to_add)}")

    # Формируем итоговый список: [owner, ...existing, ...to_add]
    # Владелец должен быть первым
    final_devices = [owner_address]
    seen = {owner_address}
    for a in existing:
        if a not in seen:
            final_devices.append(a)
            seen.add(a)
    for a in to_add:
        if a not in seen:
            final_devices.append(a)
            seen.add(a)

    print(f"[*] Итоговый список устройств: {len(final_devices)}")

    if args.dry_run:
        print("\n[DRY-RUN] Транзакция не отправлена.")
        print("Список устройств для setDevices:")
        for i, addr in enumerate(final_devices):
            mark = " (owner)" if addr == owner_address else " (new)" if addr in to_add else ""
            print(f"  {i+1}. {addr}{mark}")
        sys.exit(0)

    # Формируем экстринзик
    # Вариант 1: setDevices(devices) — Polkadot / новый runtime
    # Вариант 2: add(devices, account) по одному — Kusama / robonomics.app
    print("[*] Формирование и отправка транзакции...")

    extrinsic = None
    pallet_used = None

    # Пробуем setDevices (BoundedVec: Kusama — (list,), Polkadot — list)
    for pallet in ("RWS", "Rws", "rws"):
        for func in ["set_devices", "setDevices"]:
            for devices_param in [(final_devices,), final_devices]:
                try:
                    inner_call = substrate.compose_call(
                        call_module=pallet,
                        call_function=func,
                        call_params={"devices": devices_param},
                    )
                    pallet_used = pallet
                    try:
                        extrinsic = substrate.compose_call(
                            call_module=pallet,
                            call_function="call",
                            call_params={
                                "subscription_id": owner_address,
                                "call": inner_call,
                            },
                        )
                    except Exception:
                        extrinsic = inner_call
                except Exception:
                    continue
                else:
                    break
            else:
                continue
            break
        else:
            continue
        break

    # Fallback: add(devices, account) по одному для каждого нового — Kusama
    if extrinsic is None and to_add:
        for pallet in ("RWS", "Rws", "rws"):
            add_calls = []
            current_devices = [owner_address] + [
                a for a in existing if a != owner_address
            ]
            ok = True
            for new_addr in to_add:
                added = False
                for func in ["add", "Add"]:
                    for params in [
                        {"devices": current_devices, "account": new_addr},
                        {"devices": current_devices, "address": new_addr},
                    ]:
                        try:
                            inner = substrate.compose_call(
                                call_module=pallet,
                                call_function=func,
                                call_params=params,
                            )
                            add_call = substrate.compose_call(
                                call_module=pallet,
                                call_function="call",
                                call_params={
                                    "subscription_id": owner_address,
                                    "call": inner,
                                },
                            )
                            add_calls.append(add_call)
                            current_devices = current_devices + [new_addr]
                            added = True
                            break
                        except Exception:
                            continue
                    if added:
                        break
                if not added:
                    ok = False
                    break
            if ok and add_calls:
                pallet_used = pallet
                if len(add_calls) == 1:
                    extrinsic = add_calls[0]
                else:
                    extrinsic = substrate.compose_call(
                        call_module="Utility",
                        call_function="batch",
                        call_params={"calls": add_calls},
                    )
                break

    if extrinsic is None:
        print("Ошибка: RWS.setDevices и RWS.add не найдены в runtime.")
        print("Проверьте сеть (Kusama/Polkadot) и RPC.")
        sys.exit(1)

    # Подпись и отправка
    try:
        signed = substrate.create_signed_extrinsic(
            call=extrinsic,
            keypair=keypair,
        )
        receipt = substrate.submit_extrinsic(signed, wait_for_inclusion=True)
    except Exception as e:
        print(f"Ошибка отправки транзакции: {e}")
        sys.exit(1)

    if receipt.is_success:
        print(f"\n[OK] Транзакция включена в блок: {receipt.block_hash}")
        print(f"     Extrinsic hash: {receipt.extrinsic_hash}")
    else:
        print(f"\n[ОШИБКА] Транзакция не удалась: {receipt.error_message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
