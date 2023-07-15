import * as IPFS from 'ipfs-core'
import { create } from 'ipfs-http-client'
import Web3 from 'web3';
import { readFileSync } from "fs";
import BigNumber from "bignumber.js";

let config = readFileSync(`config/config.json`)
config = JSON.parse(config)
const web3 = new Web3(config.http_node_provider)
web3.eth.accounts.wallet.add(config.spot_pk)

const ipfs = create()

class Agent {
    constructor() {
        this.demand = {}
        this.offer = {}
        this.liabilityAddress = ""
        this.factoryABI = this.readABI()
        this.onDemandMsg = this.onDemandMsg.bind(this); // to send context of the Provider into function
        this.onSpotMsg = this.onSpotMsg.bind(this);
        this.createOffer = this.createOffer.bind(this);
        this.ipfsSubscribe()
        
    }

    async ipfsSubscribe() {
        await ipfs.pubsub.subscribe(config.provider_ipfs_topic, this.onDemandMsg)
        console.log(`subscribed to ${config.provider_ipfs_topic}`)
        await ipfs.pubsub.subscribe(config.spot_ipfs_topic, this.onSpotMsg)
        console.log(`subscribed to ${config.spot_ipfs_topic}`)

    }

    async onDemandMsg(msg) {
        let stringMsg = ""
        stringMsg = String.fromCharCode(...Array.from(msg.data))
        let m = JSON.parse(stringMsg) 
        // if (msg.from == config.ipfs_id_dapp) {
            if (m.sender == config.test_user_address) {
                stringMsg = String.fromCharCode(...Array.from(msg.data))
                this.demand = JSON.parse(stringMsg) 
                this.offer = await this.createOffer()
                console.log("Offer:")
                console.log(this.offer)
                await this.sendOffer()
            }
    }

    onSpotMsg(msg) {
        console.log(`New msg from Spot: ${msg}`)
    }

    async sendOffer() {
        const offerMsg = JSON.stringify(this.offer)
        await ipfs.pubsub.publish(config.provider_ipfs_topic, offerMsg)
        console.log(`offer published to ${config.provider_ipfs_topic}`)
    }

    readABI() {
        let abi = readFileSync(`abi/Factory.json`)
        let factoryABI = JSON.parse(abi)
        return factoryABI
    }

    async createOffer() {
        this.factory = await new web3.eth.Contract(this.factoryABI, config.factory_contract_address)
        let offer =
        {
            model: this.demand.model
            , objective: this.demand.objective
            , token: this.demand.token
            , cost: this.demand.cost
            , validator: this.demand.validator
            , lighthouse: this.demand.lighthouse
            , lighthouseFee: 1
            , deadline: await web3.eth.getBlockNumber() + 100000
            , nonce: BigNumber(await this.factory.methods.nonceOf(config.spot_address).call()).toNumber()
            , sender: config.spot_address
        };
    
        const hash = web3.utils.soliditySha3(
            { t: 'bytes', v: offer.model },
            { t: 'bytes', v: offer.objective },
            { t: 'address', v: offer.token },
            { t: 'uint256', v: offer.cost },
            { t: 'address', v: offer.validator },
            { t: 'address', v: offer.lighthouse },
            { t: 'uint256', v: offer.lighthouseFee },
            { t: 'uint256', v: offer.deadline },
            { t: 'uint256', v: offer.nonce },
            { t: 'address', v: offer.sender }
        );
        offer.signature = await web3.eth.accounts.sign(hash, config.spot_pk);
        return offer;
    }
}

const agent = new Agent()
