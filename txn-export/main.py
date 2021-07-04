from dataclasses import dataclass
import requests
import json
import os
import xlsxwriter
import tkinter as tk
from datetime import datetime


class Client:
    """JSON-RPC Client."""

    def __init__(
        self,
        testnet=False,
        username=None,
        password=None,
        ip=None,
        port=None,
        directory=None,
    ):

        if not ip:
            self.ip = "localhost"  # default to localhost
        else:
            self.ip = ip

        self.username = username
        self.password = password

        if testnet is True:
            self.testnet = True
            self.port = 9904
            self.url = "http://{0}:{1}".format(self.ip, self.port)
        else:
            self.testnet = False
            self.port = 9902
            self.url = "http://{0}:{1}".format(self.ip, self.port)
        if port is not None:
            self.port = port
            self.url = "http://{0}:{1}".format(self.ip, self.port)

        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({"content-type": "application/json"})

    def req(self, method, params=()):
        """send request to peercoind"""

        response = self.session.post(
            self.url,
            data=json.dumps({"method": method, "params": params, "jsonrpc": "1.1"}),
        ).json()

        if response["error"] is not None:
            return response["error"]
        else:
            return response["result"]

    def batch(self, reqs):
        """send batch request using jsonrpc 2.0"""

        batch_data = []

        for req_id, req in enumerate(reqs):
            batch_data.append(
                {"method": req[0], "params": req[1], "jsonrpc": "2.0", "id": req_id}
            )

        data = json.dumps(batch_data)
        response = self.session.post(self.url, data=data).json()
        return response

    def listtransactions(self, count=999999, skip=0, include_watchonly=False):
        """Returns up to 'count' most recent transactions."""
        return self.req("listtransactions", ["*", count, skip, include_watchonly])

    def getrawtransaction(self, txid, verbose=True):
        """return getrawtransaction from peercoind"""
        return self.req("getrawtransaction", [txid, verbose])


@dataclass
class Mint:

    reward: float
    blocktime: int
    txid: str
    address: str
    utxo: str
    utxo_amount: float
    utxo_age: int

    def values(self):
        return [
            self.txid,
            self.blocktime,
            self.address,
            self.utxo_age,
            self.utxo_amount,
            self.reward,
        ]


@dataclass
class Monetary:

    address: str
    amount: int
    txid: str
    timestamp: int
    io: str

    def values(self):
        return [
            self.txid,
            self.timestamp,
            self.address,
            self.amount,
            self.io,
        ]


def filter_txn(node, raw_txn: dict):

    if raw_txn["category"] == "stake-mint":

        return Mint(
            reward=raw_txn["amount"],
            txid=raw_txn["txid"],
            blocktime=raw_txn["blocktime"],
            address=raw_txn["address"],
            utxo=node.getrawtransaction(raw_txn["txid"])["vin"][0]["txid"],
            utxo_amount=utxo_amount(node, raw_txn["txid"]),
            utxo_age=utxo_age(node, raw_txn["txid"]),
        )

    if raw_txn["category"] == "stake":

        return Mint(
            reward=raw_txn["amount"],
            txid=raw_txn["txid"],
            blocktime=raw_txn["blocktime"],
            address=raw_txn["address"],
            utxo=node.getrawtransaction(raw_txn["txid"])["vin"][0]["txid"],
            utxo_amount=utxo_amount(node, raw_txn["txid"]),
            utxo_age=utxo_age(node, raw_txn["txid"]),
        )

    else:
        return Monetary(
            amount=raw_txn["amount"],
            txid=raw_txn["txid"],
            timestamp=raw_txn["time"],
            address=raw_txn["address"],
            io=raw_txn["category"],
        )

def utxo_age(node, txid: str) -> int:
    """find out the age of the UTXO"""

    raw = node.getrawtransaction(txid)

    utxo_blocktime = raw["blocktime"]
    vin = raw["vin"][0]["txid"]
    vin_time = node.getrawtransaction(vin)["blocktime"]

    return utxo_blocktime - vin_time


def utxo_amount(node, txid: str) -> int:
    """find out UTXO amount"""

    raw = node.getrawtransaction(txid)
    vin = node.getrawtransaction(raw["vin"][0]["txid"])
    vin_amount = vin["vout"][1]["value"]

    return vin_amount


def export_to_excel():

    node = Client(
        testnet=chkValue.get(),
        username=username.get(),
        password=password.get(),
        ip="localhost",
    )
    listtxns = [filter_txn(node, i) for i in node.listtransactions()]

    with xlsxwriter.Workbook("peercoin_export.xlsx") as workbook:

        mints_worksheet = workbook.add_worksheet("Mints")

        mints_worksheet.write("A1", "TXID")
        mints_worksheet.set_column("A:A", 80)
        mints_worksheet.write("B1", "Blocktime")
        mints_worksheet.set_column("B:B", 25)
        mints_worksheet.write("C1", "Address")
        mints_worksheet.set_column("C:C", 50)
        mints_worksheet.write("D1", "UTXO age")
        mints_worksheet.set_column("D:D", 20)
        mints_worksheet.write("E1", "UTXO amount")
        mints_worksheet.set_column("E:E", 20)
        mints_worksheet.write("F1", "Reward")
        mints_worksheet.set_column("F:F", 20)

        mints = [i.values() for i in listtxns if isinstance(i, Mint)]

        mints_worksheet.add_table(
            f"A3:F{len(mints)+5}", {"data": mints, "header_row": False}
        )

        ## Spend / Recieve table

        monetary_worksheet = workbook.add_worksheet("Monetary")

        monetary_worksheet.write("A1", "TXID")
        monetary_worksheet.set_column("A:A", 80)
        monetary_worksheet.write("B1", "Timestamp")
        monetary_worksheet.set_column("B:B", 25)
        monetary_worksheet.write("C1", "Address")
        monetary_worksheet.set_column("C:C", 55)
        monetary_worksheet.write("D1", "Amount")
        monetary_worksheet.set_column("D:D", 20)
        monetary_worksheet.write("E1", "In/Out")
        monetary_worksheet.set_column("E:E", 20)

        monetaries = [i.values() for i in listtxns if isinstance(i, Monetary)]

        monetary_worksheet.add_table(
            f"A3:E{len(monetaries)+5}", {"data": monetaries, "header_row": False}
        )

if __name__ == "__main__":

    ## Init tkiter window

    root = tk.Tk()
    root.title("Peercoin Transaction Export")
    canvas1 = tk.Canvas(root, width=300, height=200)
    canvas2 = tk.Canvas(root, width=100, height=100)
    canvas2.pack()
    canvas1.pack()

    ## Testnet checkbox

    chkValue = tk.BooleanVar()
    chkValue.set(True)

    chk = tk.Checkbutton(root, text="Testnet?", var=chkValue)
    canvas1.create_window(150, 35, window=chk)

    ## RPC username/pass
    username = tk.Entry(canvas2, width=20)
    username.insert(0, "RPC Username")
    username.pack(padx=5, pady=5)

    password = tk.Entry(canvas2, width=15)
    password.insert(0, "RPC Password")
    password.pack(padx=5, pady=5)

    ## Run button

    button1 = tk.Button(text="Run!", command=export_to_excel, bg="brown", fg="white")
    canvas1.create_window(150, 120, window=button1)

    root.mainloop()
