#!/bin/bash
#git clone https://github.com/changjunkun/aws.git
cd /root/cjk/aws
#升级pip，npm版本为 pip:24.3.1  npm：11.0.0

/root/.venv/bin/python3 -m pip install --upgrade pip
pip --version
npm install -g npm@11.0.0 --force
#检查npm是否升级到11.0.0版本
npm --version 
#安装ckd工具
sudo npm install -g aws-cdk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
