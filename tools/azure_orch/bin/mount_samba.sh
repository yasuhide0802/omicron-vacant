sudo mkdir /code_point
sudo chomd 777 /code_point
sudo mount -t cifs -o username=$ADMIN_USERNAME,password=maro_dist //$SAMBA_IP/sambashare /code_point