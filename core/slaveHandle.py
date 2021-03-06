# -*- coding: utf-8 -*-
__time__ = '2018/3/6 14:29'
__author__ = 'winkyi@163.com'
import json,sys
from utils.utils import *
from utils import log
from backend.transfer import Transfer
from utils.encrypt import MyCrypt

logger = log.Log()
dc = MyCrypt()


class SlaveHandle(object):
    def __init__(self,param):
        self.param_dic = json.loads(param)
        try:
            if self.param_dic['operate'] in ['backup','update','restore']:
                self.getProjectParam()
                self.getVersionLibParam()
                self.transfer = Transfer(self.versionLib_ip,self.versionLib_sshPort,self.versionLib_hostname,self.versionLib_password)
            elif self.param_dic['operate'] == 'distribute':
                self.getFileParam()
                self.getMasterParam()
                self.transfer = Transfer(self.master_ip,self.master_sshPort,self.master_hostname,self.master_password)
        except KeyError:
            logger.exception("param_dic has not key!please check!!")
            sys.exit('slave param error,process exit')
        except Exception:
            logger.exception("init slave param fail!!!")




    def getProjectParam(self):
        self.project_backupPath = str(getHomePath()+'/'+self.param_dic['project']['project_backupPath'])
        self.project_name = str(self.param_dic['project']['project_name'])
        self.project_path = str(getHomePath()+'/'+self.param_dic['project']['project_path'])
        self.project_versionLib = str(getHomePath()+'/'+self.param_dic['project']['project_versionLib'] +'/' +getCurrentDay())
        self.project_tgzName = str(self.param_dic['project']['project_tgzName'])


    def getMasterParam(self):
        self.master_ip = str(self.param_dic['master']['master_ip'])
        self.master_hostname = str(self.param_dic['master']['master_hostname'])
        self.master_sshPort = int(self.param_dic['master']['master_sshPort'])
        self.master_password = str(dc.decrypt(self.param_dic['master']['master_password']))


    def getVersionLibParam(self):
        self.versionLib_path = str(self.param_dic['version']['versionLib_path'] +'/' +getCurrentDay())
        self.versionLib_ip = str(self.param_dic['version']['versionLib_ip'])
        self.versionLib_sshPort = int(self.param_dic['version']['versionLib_sshPort'])
        self.versionLib_hostname = str(self.param_dic['version']['versionLib_hostname'])
        self.versionLib_password = str(dc.decrypt(self.param_dic['version']['versionLib_password']))


    def getFileParam(self):
        self.remoteFile = self.param_dic['file']['remoteFile']
        self.soureFile = self.param_dic['file']['soureFile']

    def handle(self):
        #备份操作
        if self.param_dic['operate'] == 'backup':
            print "backup project %s" %self.param_dic['project']['backup']
            self.backup(self.project_backupPath,self.project_name,self.project_path)

        #更新操作
        if  self.param_dic['operate'] == 'update':
            print "update project %s" %self.param_dic['project']['update']
            #更新操作前必须要备份
            self.backup(self.project_backupPath,self.project_name,self.project_path)
            #更新操作
            self.update(self.project_versionLib,self.project_name,self.project_path,self.project_backupPath)

        #回退操作
        if  self.param_dic['operate'] == 'restore':
            print "restore project %s" %self.param_dic['project']['restore']

        #文件分发操作
        if self.param_dic['operate'] == 'distribute':
            self.distribute()


    def backup(self,project_backupPath,project_name,project_path):
        if not isPath(project_path):
            logger.error("project %s is not exist,don't excute backup operate!!!!!" % project_path)
        else:
            if pathIsExists(project_backupPath):
                try:
                    logger.info("start backup project")
                    print "project_path:",project_path
                    print "project_backupPath:",project_backupPath
                    print "project_name:",project_name
                    self.backup_project_name = "%s_%s" %(project_name,getCurrentTime())
                    makeTar(project_path,project_backupPath,self.backup_project_name)
                except:
                    logger.exception("backup fail: tar cmd error!!!")
            else:
                logger.error("backup path is error!!!")


    #更新操作
    #project_name工程包的名称
    #self.project_name备份后工程包的名称，已带上日期
    def update(self,project_versionLib,project_name,project_path,project_backupPath):
        #判断本地版本库路径是否存在,不存在就创建
        if pathIsExists(project_versionLib):
            if pathIsExists(project_path):
                #判断备份是否完成
                if fileIsExist("%s/%s.tar.gz"  %(project_backupPath,self.backup_project_name)) and getFileSize("%s/%s.tar.gz"%(project_backupPath,self.backup_project_name))  > 0:
                    #从版本机获取版本至本地版本放置路径
                    logger.info("start get remote verionLib project!")
                    self.transfer.sftp_down_file('%s/%s' %(self.versionLib_path,self.project_tgzName),'%s/%s' %(project_versionLib,self.project_tgzName))
                    logger.info("success get remote versionLib project!")
                    #删除旧版本目录
                    delDir(self.project_path)
                    #从本地版本解压包至工程目录
                    if isNullDir(self.project_path):
                        unTar(self.project_versionLib,self.project_tgzName,self.project_path)
                    else:
                        logger.info("project path is not null,please empty path!")
                    #配置环境变量,看情况

                    #启动工程
                    """
                    #!/bin/bash
                    JAVA_HOME=/home/xinli/jdk1.8.0_92
                    JAVA=$JAVA_HOME/bin/java
                    nohup $JAVA -jar yunnan-rest-service-0.1.0.jar -Djava.ext.dirs=$JAVA_HOME/lib &
                """

                    #检查启动情况

                else:
                    logger.error("UPDATE:[backupfile is not find ,update operate stop!]")
            else:
                logger.error("UPDATE:[create project path fail!]")
        else:
            logger.error("UPDATE:[create versionLib path fail!]")


    def restore(self):
        logger.info("funcion development pending")




    def distribute(self):
        #去除路径后的类似.txt等字段
        remotePath = "/".join(self.remoteFile.split('/')[0:-1])
        if self.transfer.sftp_exec_command("ls -l %s" %remotePath):
            if fileIsExist(self.soureFile):
                logger.info("start distribute file")
                self.transfer.sftp_upload_file(self.remoteFile,self.soureFile)
                logger.info("success distribute file %s" %self.remoteFile)
            else:
                logger.error("local file %s is not exist" %self.soureFile)
        else:
            logger.error("remote path %s is not exist!!" %self.remotePath)


