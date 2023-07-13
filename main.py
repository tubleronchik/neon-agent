import web3
import argparse
import secrets
import json
import ipfs_api
from eth_account.messages import encode_defunct


class Agent:
    def __init__(self, config_path) -> None:
        self.config: dict = self._read_configuration(config_path)
        self.w3 = web3.Web3(web3.Web3.HTTPProvider(self.config["http_node_provider"]))
        self.liability_address = ""
        ipfs_api.pubsub_subscribe(self.config["provider_ipfs_topic"], self.on_demand_message)
        ipfs_api.pubsub_subscribe(self.config["spot_ipfs_topic"], self.on_spot_message)

    def on_demand_message(self, msg: dict) -> None:
        print(f"msg: {msg}")
        if msg["senderID"] == self.config["ipfs_id_dapp"]:
            demand = json.loads(msg["data"])
            offer = self.create_offer(demand)
            print(f"offer: {offer}")
            ipfs_api.pubsub_publish(self.config["provider_ipfs_topic"], json.dumps(offer))
            # ipfs_api.pubsub_publish(self.config["spot_ipfs_topic"], json.dumps(f"{{objective: {offer['objective']}}}"))

    def create_offer(self, demand: dict) -> dict:
        offer = {
            "model": demand["model"],
            "objective": demand["objective"],
            "token": demand["token"],
            "cost": demand["cost"],
            "lighthouse": demand["lighthouse"],
            "lighthouseFee": demand["lighthouseFee"],
            "validator": demand["validator"],
            "validatorFee": demand["validatorFee"],
            "deadline": self.w3.eth.get_block_number() + 1000,
            "nonce": self.w3.eth.get_transaction_count(self.config["spot_address"]),
            "sender": self.config["spot_address"],
        }
        types = [
            "bytes",
            "bytes",
            "address",
            "uint256",
            "address",
            "uint256",
            "address",
            "uint256",
            "uint256",
            "uint256",
            "address",
        ]

        hash = web3.Web3.soliditySha3(
            types,
            [
                str.encode(offer["model"]),
                str.encode(offer["objective"]),
                offer["token"],
                self.w3.toInt(hexstr=offer["cost"]),
                offer["lighthouse"],
                self.w3.toInt(hexstr=offer["lighthouseFee"]),
                offer["validator"],
                self.w3.toInt(hexstr=offer["validatorFee"]),
                offer["deadline"],
                offer["nonce"],
                offer["sender"],
            ],
        )
        msg = encode_defunct(hash)
        offer["signature"] = str(web3.eth.Account.sign_message(msg, private_key=self.config["spot_pk"]).signature.hex())  
        return offer

    def on_spot_message(self, msg: dict) -> None:  # result
        if msg["senderID"] == self.config["ipfs_id_spot"]:
            ipfs_hash = json.loads(msg["data"])["result"]

    def create_result_msg(self, ipfs_hash: str) -> dict:
        result = {"address": self.liability_address, result: ipfs_hash, "success": True}


    def _read_configuration(self, path: str) -> dict | None:
        """Internal method. Loads the configuration.
        :param config_path: Path to the configuration file.
        :return: Python dict with the config
        """

        try:
            with open(path) as f:
                content = f.read()
                config = json.loads(content)
                return config
        except Exception as e:
            print(f"Couldn't load the configuration file: {e}")


def run() -> None:
    """Main function of the script. Read the config path as the argument from the command line."""

    parser = argparse.ArgumentParser(description="Add config path.")
    parser.add_argument("config_path", type=str, help="config path")
    args = parser.parse_args()
    Agent(args.config_path)


if __name__ == "__main__":
    run()
