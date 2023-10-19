import os
import socketio
import logging
from print_utils import pdf_render_print

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sio = socketio.Client()

@sio.on('connect')
def on_connect():
    """Callback for when the client successfully connects to the server."""
    logger.info("Connected to the server.")

@sio.on('disconnect')
def on_disconnect():
    """Callback for when the client disconnects from the server."""
    logger.info("Disconnected from the server.")

@sio.on('print')
def on_print(data):
    """Callback for handling 'print' events from the server."""
    order_id = data.get('order_id')
    if order_id:
        logger.info(f"Received order ID: {order_id}")
        try:
            pdf_render_print(order_id)
        except Exception as e:
            logger.error(f"Error while processing order ID {order_id}: {e}")
    else:
        logger.warning("Received 'print' event without order ID.")

def main():
    """Main function to start the client."""
    link = os.environ.get('link')
    if not link:
        logger.error("Environment variable 'link' not set.")
        return
    
    try:
        sio.connect(link)
        sio.wait()
    except Exception as e:
        logger.error(f"Error connecting to server: {e}")

if __name__ == "__main__":
    main()
