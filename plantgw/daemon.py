"""Run PlantGateway as daemon."""
from plantgw.plantgateway import PlantGateway

CONFIG_FILE_PATH = "/etc/plantgateway.yaml"

# TODO:
#  - exit gracefully when killed


def main():
    pg = PlantGateway(CONFIG_FILE_PATH)
    pg.start_daemon()


if __name__ == '__main__':
    main()
