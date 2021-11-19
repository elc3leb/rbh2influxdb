# Robinhood to Influxdb

## Purpose 

Simply parse generated [robinhood](https://github.com/cea-hpc/robinhood) logs files and push it to an influxdb sgdb.

Link to a Grafana frontend, you can create a dashboard like that.

![Screenshot](image.png)


## Usage

Call `rbh2influxdb.py` just after your robinhood run through a script like that: 

The script detects if it is a scan or a clean 

```
${PATH}/rbh2influxdb.py --log robinhood.log
```

## Dockerfile 

You can also use the Dockerfile to build your own container, it is set for Lutre Filesystem, which explains the Lustre parameter `ldlm.namespaces. *. lru_max_age` in the Makefile 
