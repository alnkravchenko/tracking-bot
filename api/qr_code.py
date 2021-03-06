import qrcode
import cv2 as cv
from io import BytesIO
from os import remove


class QRCodeDoesNotExist(Exception):
    ...


def get_qr_code_data(file: str) -> str:
    img = cv.imread(file)
    detector = cv.QRCodeDetector()
    try:
        data_, points, _ = detector.detectAndDecode(img)
    except cv.error:
        raise TypeError('File is invalid')
    if points is None:
        raise QRCodeDoesNotExist('QR Code does not exist or hasn\'t been recognized')
    return data_


def new_qr_code(data_, filename, ver=1, err_cor=qrcode.constants.ERROR_CORRECT_H, size=1, border=4, fg_color='black', bg_color='white', space='RGB') -> str:
    qr = qrcode.QRCode(version=ver, error_correction=err_cor, box_size=size, border=border)
    qr.add_data(data_)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fg_color, back_color=bg_color).convert(space)
    img.save(f'./images/qr_codes/{filename}')
    return filename


def save_photo(file: BytesIO, filename: str):
    with open(get_file_path(filename), 'wb') as out:
        out.write(file.getbuffer())


get_file_path = lambda filename: f'./images/{filename}.jpg'


delete_file = lambda filename: remove(filename)


if __name__ == '__main__':
    control = ['asdasAD123134FGSD','asdas4FGSD', '52352SD', '52352342342SD', '524562111SD', '52352678678SD', '367721Fasdf']
    for index, element in enumerate(control):
        new_qr_code(f'{index+1} {element}', f'data{index}.png', ver=4, size=4)
    # get_qr_code_data('1.jpg')
    # get_qr_code_data('2.jpg')
    #print(get_qr_code_data('data0.png'))
