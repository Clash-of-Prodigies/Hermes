import time
import logging
import oreiades
from adapters import ADAPTERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def process_one(conn):
    msg = oreiades.get_next_queued_message(conn)
    if not msg:
        return False
    
    channel = msg.get("channel", "email")
    adapter = ADAPTERS.get(channel)

    if not adapter:
        logging.error(f"No adapter found for channel: {channel}")
        oreiades.mark_failed(conn, msg["id"], f"No adapter for channel: {channel}")
        return True

    logging.info(f"Processing message id={msg['id']} to={msg['recipient']}")

    try:
        subject = msg.get('subject', 'No Subject')
        data = msg.get("data", {})

        try:
            adapter.send(
                to=msg.get("recipient", ""),
                subject=subject,
                data=data,
                template_name=msg.get("template", "default"),
            )
        except Exception as e:
            logging.error(f"Error sending email for message {msg['id']}: {e}")
            raise
        else:
            oreiades.mark_sent(conn, msg["id"])
            logging.info(f"Message {msg['id']} sent.")

    except Exception as e:
        logging.exception(f"Failed sending message {msg['id']}")
        attempts = oreiades.increment_attempts(conn, msg["id"], str(e))

        if oreiades.should_give_up(attempts):
            oreiades.mark_failed(conn, msg["id"], str(e))
            logging.warning(f"Message {msg['id']} marked failed.")

    return True


def main():
    logging.info("Starting worker...")
    while True:
        try:
            with oreiades.get_connection() as conn:
                worked = process_one(conn)
                if not worked: time.sleep(2)
        except KeyboardInterrupt:
            logging.info("Shutting down worker.")
            break
        except Exception as e: logging.exception(f"Worker encountered an error: {e}")

if __name__ == "__main__":
    main()
