import string
import os.path
import urllib

#
# Project:
#   glideinWMS
#
# File Version: 
#
# Description:
#   Frontend config related classes
#

############################################################
#
# Configuration
#
############################################################

class FrontendConfig:
    def __init__(self):
        # set default values
        # user should modify if needed

        self.frontend_descript_file = "frontend.descript"
        self.group_descript_file = "group.descript"
        self.params_descript_file = "params.cfg"
        self.signature_descript_file = "signatures.sha1"
        self.signature_type = "sha1"

# global configuration of the module
frontendConfig=FrontendConfig()


############################################################
#
# Generic Class
# You most probably don't want to use these
#
############################################################

# loads a file or URL composed of
#   NAME VAL
# and creates
#   self.data[NAME]=VAL
# It also defines:
#   self.config_file="name of file"
class ConfigFile:
    def __init__(self,config_dir,config_file,convert_function=repr,
                 validate=None): # if defined, must be (hash_algo,value)
        self.config_dir=config_dir
        self.config_file=config_file
        self.data={}
        self.load(os.path.join(config_dir,config_file),convert_function,validate)
        self.derive()

    def open(self,fname):
        if (fname[:5]=="http:") or (fname[:6]=="https:") or (fname[:4]=="ftp:"):
            # one of the supported URLs
            return urllib.urlopen(fname)
        else:
            # local file
            return open(fname,"r")
        

    def validate_func(self,data,validate,fname):
        if validate!=None:
            import hashCrypto
            vhash=hashCrypto.get_hash(validate[0],data)
            if vhash!=validate[1]:
                raise IOError, "Failed validation of '%s'. Hash %s computed to '%s', expected '%s'"%(fname,validate[0],vhash,validate[1])

    def load(self,fname,convert_function,
             validate=None): # if defined, must be (hash_algo,value)
        self.data={}
        fd=self.open(fname)
        try:
            data=fd.read()
            self.validate_func(data,validate,fname)
            lines=data.splitlines()
            del data
            for line in lines:
                if line[0]=="#":
                    continue # comment
                if len(string.strip(line))==0:
                    continue # empty line
                self.split_func(line,convert_function)
        finally:
            fd.close()

    def split_func(self,line,convert_function):
        larr=string.split(line,None,1)
        lname=larr[0]
        if len(larr)==1:
            lval=""
        else:
            lval=larr[1][:-1] #strip newline
        exec("self.data['%s']=%s"%(lname,convert_function(lval)))

    def derive(self):
        return # by default, do nothing
    
    def __str__(self):
        output = '\n'
        for key in self.data.keys():
            output += '%s = %s, (%s)\n' % (key, str(self.data[key]), type(self.data[key]))
        return output

# load from the group subdir
class GroupConfigFile(ConfigFile):
    def __init__(self,base_dir,group_name,config_file,convert_function=repr,
                 validate=None): # if defined, must be (hash_algo,value)
        ConfigFile.__init__(self,os.path.join(base_dir,"group_"+group_name),config_file,convert_function,validate)
        self.group_name=group_name

# load both the main and group subdir config file
# and join the results
class JoinConfigFile(ConfigFile):
    def __init__(self,base_dir,group_name,config_file,convert_function=repr,
                 main_validate=None,group_validate=None): # if defined, must be (hash_algo,value)
        ConfigFile.__init__(self,base_dir,config_file,convert_function,main_validate)
        self.group_name=group_name
        group_obj=GroupConfigFile(base_dir,group_name,config_file,convert_function,group_validate)
        #merge by overriding whatever is found in the subdir
        for k in group_obj.data.keys():
            self.data[k]=group_obj.data[k]

############################################################
#
# Configuration
#
############################################################

class FrontendDescript(ConfigFile):
    def __init__(self,config_dir):
        global frontendConfig
        ConfigFile.__init__(self,config_dir,frontendConfig.frontend_descript_file,
                            repr) # convert everything in strings
        

class ElementDescript(GroupConfigFile):
    def __init__(self,base_dir,group_name):
        global frontendConfig
        GroupConfigFile.__init__(self,base_dir,group_name,frontendConfig.group_descript_file,
                                 repr) # convert everything in strings

class ParamsDescript(JoinConfigFile):
    def __init__(self,base_dir,group_name):
        global frontendConfig
        JoinConfigFile.__init__(self,base_dir,group_name,frontendConfig.params_descript_file,
                                lambda s:"('%s',%s)"%tuple(s.split(None,1))) # split the array
        self.const_data={}
        self.expr_data={} # original string
        self.expr_objs={}  # compiled object
        for k in self.data.keys():
            type_str,val=self.data[k]
            if type_str=='EXPR':
                self.expr_objs[k]=compile(val,"<string>","eval")
                self.expr_data[k]=val
            elif type_str=='CONST':
                self.const_data[k]=val
            else:
                raise RuntimeError, "Unknown parameter type '%s' for '%s'!"%(type_str,k)

class SignatureDescript(ConfigFile):
    def __init__(self,config_dir):
        global frontendConfig
        ConfigFile.__init__(self,config_dir,frontendConfig.signature_descript_file,
                            None) # Not used, redefining split_func
        self.signature_type=frontendConfig.signature_type

    def split_func(self,line,convert_function):
        larr=string.split(line,None)
        if len(larr)!=3:
            raise RuntimeError, "Invalid line (expected 3 elements, found %i)"%len(larr)
        self.data[larr[2]]=(larr[0],larr[1])

############################################################
#
# Processed configuration
#
############################################################

# not everything is merged
# the old element can still be accessed
class ElementMergedDescript:
    def __init__(self,base_dir,group_name):
        self.frontend_data=FrontendDescript(base_dir).data
        if not (group_name in string.split(self.frontend_data['Groups'],',')):
            raise RuntimeError, "Group '%s' not supported: %s"%(group_name,self.frontend_data['Groups'])
        
        self.element_data=ElementDescript(base_dir,group_name).data
        self.group_name=group_name

        self.merge()

    #################
    # Private
    def merge(self):
        self.merged_data={}

        for t in ('JobSchedds',):
            self.merged_data[t]=self.split_list(self.frontend_data[t])+self.split_list(self.element_data[t])
            if len(self.merged_data[t])==0:
                raise RuntimeError,"Found empty %s!"%t
        for t in ('FactoryCollectors',):
            self.merged_data[t]=eval(self.frontend_data[t])+eval(self.element_data[t])
            if len(self.merged_data[t])==0:
                raise RuntimeError,"Found empty %s!"%t
        for t in ('FactoryQueryExpr','JobQueryExpr'):
            self.merged_data[t]="(%s) && (%s)"%(self.frontend_data[t],self.element_data[t])
        for t in ('FactoryMatchAttrs','JobMatchAttrs'):
            attributes=[]
            names=[]
            for el in eval(self.frontend_data[t])+eval(self.element_data[t]):
                el_name=el[0]
                if not (el_name in names):
                    attributes.append(el)
                    names.append(el_name)
            self.merged_data[t]=attributes
        for t in ('MatchExpr',):
            self.merged_data[t]="(%s) and (%s)"%(self.frontend_data[t],self.element_data[t])
            self.merged_data[t+'CompiledObj']=compile(self.merged_data[t],"<string>","eval")

        self.merged_data['ProxySelectionPlugin']='ProxyAll' #default
        for t in ('ProxySelectionPlugin','SecurityName'):
            for data in (self.frontend_data,self.element_data):
                if data.has_key(t):
                    self.merged_data[t]=data[t]

        proxies=[]
        for data in (self.frontend_data,self.element_data):
            if data.has_key('Proxies'):
                proxies+=eval(data['Proxies'])
        self.merged_data['Proxies']=proxies

        proxy_security_classes={}
        for data in (self.frontend_data,self.element_data):
            if data.has_key('ProxySecurityClasses'):
                dprs=eval(data['ProxySecurityClasses'])
                for k in dprs.keys():
                    proxy_security_classes[k]=dprs[k]
        self.merged_data['ProxySecurityClasses']=proxy_security_classes
        
        proxy_trust_domains={}
        for data in (self.frontend_data,self.element_data):
            if data.has_key('ProxyTrustDomains'):
                dprs=eval(data['ProxyTrustDomains'])
                for k in dprs.keys():
                    proxy_trust_domains[k]=dprs[k]
        self.merged_data['ProxyTrustDomains']=proxy_trust_domains

        proxy_types={}
        for data in (self.frontend_data,self.element_data):
            if data.has_key('ProxyTypes'):
                dprs=eval(data['ProxyTypes'])
                for k in dprs.keys():
                    proxy_types[k]=dprs[k]
        self.merged_data['ProxyTypes']=proxy_types

        proxy_key_files={}
        for data in (self.frontend_data,self.element_data):
            if data.has_key('ProxyKeyFiles'):
                dprs=eval(data['ProxyKeyFiles'])
                for k in dprs.keys():
                    proxy_key_files[k]=dprs[k]
        self.merged_data['ProxyKeyFiles']=proxy_key_files

        proxy_pilot_files={}
        for data in (self.frontend_data,self.element_data):
            if data.has_key('ProxyPilotFiles'):
                dprs=eval(data['ProxyPilotFiles'])
                for k in dprs.keys():
                    proxy_pilot_files[k]=dprs[k]
        self.merged_data['ProxyPilotFiles']=proxy_pilot_files

        proxy_vm_ids={}
        for data in (self.frontend_data,self.element_data):
            if data.has_key('ProxyVMIds'):
                dprs=eval(data['ProxyVMIds'])
                for k in dprs.keys():
                    proxy_vm_ids[k]=dprs[k]
        self.merged_data['ProxyVMIds']=proxy_vm_ids

        proxy_vm_types={}
        for data in (self.frontend_data,self.element_data):
            if data.has_key('ProxyVMTypes'):
                dprs=eval(data['ProxyVMTypes'])
                for k in dprs.keys():
                    proxy_vm_types[k]=dprs[k]
        self.merged_data['ProxyVMTypes']=proxy_vm_types
        
        return

    def split_list(self,val):
        if val=='None':
            return []
        elif val=='':
            return []
        else:
            return string.split(val,',')
        
class GroupSignatureDescript:
    def __init__(self,base_dir,group_name):
        self.group_name=group_name
        
        sd=SignatureDescript(base_dir)
        self.signature_data=sd.data
        self.signature_type=sd.signature_type

        fd=sd.data['main']
        self.frontend_descript_fname=fd[1]
        self.frontend_descript_signature=fd[0]

        gd=sd.data['group_%s'%group_name]
        self.group_descript_fname=gd[1]
        self.group_descript_signature=gd[0]

