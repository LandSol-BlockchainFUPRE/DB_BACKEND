import base64

def image_to_bytes_and_save(image_path, output_file_path):
    """
    Converts an image to a base64 encoded byte string and saves it to a file.

    Args:
        image_path (str): The path to the input image file.
        output_file_path (str): The path where the byte file will be saved.
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())

        with open(output_file_path, "wb") as output_file:
            output_file.write(encoded_string)
        print(f"Image '{image_path}' successfully converted to bytes and saved to '{output_file_path}'.")
    except FileNotFoundError:
        print(f"Error: Image file not found at '{image_path}'")
    except Exception as e:
        print(f"An error occurred: {e}")

def bytes_to_image(input_file_path, output_image_path):
    """
    Reads a base64 encoded byte string from a file and converts it back to an image.

    Args:
        input_file_path (str): The path to the file containing the byte string.
        output_image_path (str): The path where the recovered image will be saved.
    """
    try:
        with open(input_file_path, "rb") as input_file:
            encoded_string = input_file.read()
        
        decoded_image_data = base64.b64decode(encoded_string)

        with open(output_image_path, "wb") as output_image_file:
            output_image_file.write(decoded_image_data)
        print(f"Bytes from '{input_file_path}' successfully converted back to image and saved to '{output_image_path}'.")
    except FileNotFoundError:
        print(f"Error: Byte file not found at '{input_file_path}'")
    except Exception as e:
        print(f"An error occurred: {e}")

# --- Example Usage ---
if __name__ == "__main__":
        original_image = "exp/y-300x300.png"
        byte_file = "image_bytes.bin"
        recovered_image = "recovered_image.png" # Make sure the extension matches the original image type

        # Convert image to bytes and save to a file
        image_to_bytes_and_save(original_image, byte_file)

        # Convert bytes back to an image
        bytes_to_image(byte_file, recovered_image)

        print("\nTo verify, check your current directory for 'dummy_image.png', 'image_bytes.bin', and 'recovered_image.png'.")