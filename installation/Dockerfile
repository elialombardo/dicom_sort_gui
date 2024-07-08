# Dockerfile for auto segmentation at mridian

# inherit from monai image
FROM python:3.9.10

# create install folder inside container
RUN mkdir /requirements_installation

# add requirements file to container
ADD requirements.txt /requirements_installation

# update to latest pip version 
RUN pip install -U pip

# check python version --> Python 3.9.10
RUN python --version

# install the required python packages
RUN pip install -r /requirements_installation/requirements.txt

# update libraries
RUN apt-get update 

# install plastimatch
RUN apt-get install plastimatch -y --fix-missing

