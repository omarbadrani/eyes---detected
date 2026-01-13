import cv2
import pygame
import time
import os
import numpy as np
from datetime import datetime
import csv
from scipy.spatial import distance as dist

# ============================================
# CONFIGURATION
# ============================================
CONFIG = {
    'EYE_AR_THRESHOLD': 0.20,  # Seuil EAR pour yeux fermés
    'EYE_AR_CONSEC_FRAMES': 10,  # Frames consécutifs
    'ALARM_DURATION': 5.0,
    'FRAME_WIDTH': 640,
    'FRAME_HEIGHT': 480,
    'LOG_DATA': True,
    'SHOW_FPS': True,
    'ENABLE_BEEP': True,
    'ALARM_SOUND_PATH': r"D:\Attention_Beep.wav",
    'MIN_FACE_SIZE': 100,
    'MAX_FACE_SIZE': 400,
}


# ============================================
# FONCTIONS DE DÉTECTION AMÉLIORÉES
# ============================================

def eye_aspect_ratio_simple(eye_rect):
    """Calcul EAR simplifié basé sur les dimensions de l'œil"""
    try:
        ex, ey, ew, eh = eye_rect

        # Éviter la division par zéro
        if ew == 0 or eh == 0:
            return 0.25

        # Ratio hauteur/largeur - plus réaliste pour un œil
        aspect_ratio = eh / ew

        # Convertir ratio en EAR (0.15-0.35)
        # Un œil ouvert a un ratio d'environ 0.3-0.5 (hauteur ~30-50% de la largeur)
        # Un œil fermé a un ratio < 0.2

        if aspect_ratio > 0.4:
            ear = 0.35  # Très ouvert
        elif aspect_ratio > 0.3:
            ear = 0.28  # Normalement ouvert
        elif aspect_ratio > 0.2:
            ear = 0.22  # À moitié ouvert
        elif aspect_ratio > 0.1:
            ear = 0.18  # Presque fermé
        else:
            ear = 0.15  # Fermé

        return ear
    except:
        return 0.25


class AdvancedDrowsinessDetector:
    """Détecteur avancé sans Dlib/MediaPipe"""

    def __init__(self):
        # Charger les classificateurs Haar
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )

            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )

            # Vérifier le chargement
            if self.face_cascade.empty() or self.eye_cascade.empty():
                print("❌ Impossible de charger les classificateurs")
                print("Vérifiez que les fichiers XML sont dans le bon dossier")
                print("Téléchargez depuis: https://github.com/opencv/opencv/tree/master/data/haarcascades")
                exit(1)

            print("✅ Classificateurs chargés avec succès")

        except Exception as e:
            print(f"❌ Erreur d'initialisation: {e}")
            exit(1)

        # Variables de suivi
        self.ear = 0.3
        self.eye_counter = 0
        self.blink_counter = 0
        self.drowsy_start_time = None
        self.alarm_triggered = False

        # Historique pour lissage
        self.ear_history = []
        self.history_size = 5

        # Référence EAR pour calibration
        self.ear_reference = 0.3
        self.calibrated = False
        self.calibration_frames = 0
        self.calibration_values = []

        print("✅ Détecteur avancé initialisé")

    def detect_eyes(self, roi_gray, eye_region_height):
        """Détection des yeux avec paramètres optimisés"""
        # Ajuster la taille minimale/maximale
        min_eye_size = max(15, eye_region_height // 12)
        max_eye_size = min(80, eye_region_height // 4)

        eyes = self.eye_cascade.detectMultiScale(
            roi_gray,
            scaleFactor=1.1,
            minNeighbors=5,  # Moins strict pour détecter plus d'yeux
            minSize=(min_eye_size, min_eye_size),
            maxSize=(max_eye_size, max_eye_size)
        )

        return eyes

    def calculate_ear_for_eye(self, eye_rect):
        """Calculer l'EAR pour un œil donné"""
        try:
            ex, ey, ew, eh = eye_rect

            # Calcul EAR simplifié basé sur ratio hauteur/largeur
            ear = eye_aspect_ratio_simple((ex, ey, ew, eh))

            # Ajustement basé sur la taille (les petits yeux ont tendance à paraître plus fermés)
            size_factor = min(1.0, (ew * eh) / 400)  # Normaliser
            ear = ear * (0.8 + 0.4 * size_factor)  # Ajuster entre 0.8x et 1.2x

            return min(max(ear, 0.15), 0.35)  # Limiter la plage
        except:
            return 0.25

    def detect_with_ear(self, frame, face_rect):
        """Détection utilisant l'algorithme EAR"""
        x, y, w, h = face_rect
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # ROI pour les yeux (partie supérieure du visage)
        roi_y_start = y + int(h * 0.2)  # 20% depuis le haut
        roi_height = int(h * 0.4)  # 40% de hauteur
        roi_gray = gray[roi_y_start:roi_y_start + roi_height, x:x + w]

        # Améliorer le contraste pour mieux détecter les yeux
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        roi_gray = clahe.apply(roi_gray)

        # Détecter les yeux
        eyes = self.detect_eyes(roi_gray, roi_height)

        ear_values = []
        detected_eyes = []

        for (ex, ey, ew, eh) in eyes:
            # Convertir en coordonnées absolues
            abs_ex = x + ex
            abs_ey = roi_y_start + ey

            # Filtrer les faux positifs
            aspect_ratio = ew / eh if eh > 0 else 0
            if 0.5 < aspect_ratio < 3.0:  # Ratio réaliste pour un œil
                detected_eyes.append((abs_ex, abs_ey, ew, eh))

                # Dessiner l'œil
                cv2.rectangle(frame, (abs_ex, abs_ey),
                              (abs_ex + ew, abs_ey + eh), (0, 255, 0), 2)

                # Calculer EAR pour cet œil
                ear = self.calculate_ear_for_eye((ex, ey, ew, eh))
                ear_values.append(ear)

                # Afficher l'EAR pour cet œil
                cv2.putText(frame, f"{ear:.2f}",
                            (abs_ex, abs_ey - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

        # Calculer l'EAR moyen
        if ear_values:
            self.ear = np.mean(ear_values)

            # Calibration
            if not self.calibrated and self.calibration_frames < 30:
                self.calibration_values.append(self.ear)
                self.calibration_frames += 1

                if self.calibration_frames >= 30:
                    # Prendre la valeur médiane pour éviter les outliers
                    self.ear_reference = np.median(self.calibration_values)
                    self.calibrated = True
                    print(f"✅ Calibration terminée. EAR référence: {self.ear_reference:.3f}")

            # Ajuster l'EAR par rapport à la référence
            if self.calibrated:
                adjustment = self.ear_reference / 0.28  # 0.28 est l'EAR moyen attendu
                self.ear = self.ear * adjustment
        else:
            # Si aucun œil détecté, considérer comme fermés
            self.ear = 0.15

        # Afficher le nombre d'yeux
        cv2.putText(frame, f"Yeux: {len(detected_eyes)}",
                    (x, y - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return len(detected_eyes)

    def detect(self, frame):
        """Détection principale"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Améliorer le contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        results = {
            'face_detected': False,
            'eyes_detected': 0,
            'ear': self.ear,
            'is_drowsy': False,
            'is_blinking': False,
            'blink_count': self.blink_counter,
            'eye_state': 'INCONNU'
        }

        # Détection des visages
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(CONFIG['MIN_FACE_SIZE'], CONFIG['MIN_FACE_SIZE']),
            maxSize=(CONFIG['MAX_FACE_SIZE'], CONFIG['MAX_FACE_SIZE'])
        )

        if len(faces) == 0:
            return results

        results['face_detected'] = True

        # Prendre le plus grand visage
        face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = face

        # Dessiner le rectangle du visage
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        # Zone des yeux (pour référence)
        eye_zone_y = y + int(h * 0.2)
        eye_zone_height = int(h * 0.4)
        cv2.rectangle(frame, (x, eye_zone_y),
                      (x + w, eye_zone_y + eye_zone_height),
                      (255, 255, 0), 1)

        # Détection avec EAR
        eyes_count = self.detect_with_ear(frame, face)
        results['eyes_detected'] = eyes_count

        # Lisser l'EAR avec moyenne mobile
        self.ear_history.append(self.ear)
        if len(self.ear_history) > self.history_size:
            self.ear_history.pop(0)

        smoothed_ear = np.mean(self.ear_history)
        results['ear'] = smoothed_ear

        # Détection d'état des yeux - LOGIQUE CORRIGÉE
        if eyes_count == 0:
            # Si aucun œil détecté
            results['eye_state'] = 'FERME'
            self.eye_counter += 1
            cv2.putText(frame, "FERME", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        elif smoothed_ear < CONFIG['EYE_AR_THRESHOLD']:
            # Si EAR en dessous du seuil
            results['eye_state'] = 'FERME'
            self.eye_counter += 1
            cv2.putText(frame, "FERME", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            # Yeux ouverts
            results['eye_state'] = 'OUVERT'

            # Détection de clignement
            if self.eye_counter >= 2:  # Au moins 2 frames de fermeture = clignement
                results['is_blinking'] = True
                self.blink_counter += 1
                results['blink_count'] = self.blink_counter

            # Réinitialiser
            self.eye_counter = 0
            self.drowsy_start_time = None
            self.alarm_triggered = False

            cv2.putText(frame, "OUVERT", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Vérifier la somnolence
        if self.eye_counter >= CONFIG['EYE_AR_CONSEC_FRAMES']:
            results['is_drowsy'] = True

            # Début timer
            if self.drowsy_start_time is None:
                self.drowsy_start_time = time.time()

            # Durée de somnolence
            drowsy_duration = time.time() - self.drowsy_start_time

            # Alarme après 1.5 secondes
            if drowsy_duration >= 1.5 and not self.alarm_triggered:
                self.alarm_triggered = True
                cv2.putText(frame, "SOMMOLENCE!", (x, y - 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)

        # Afficher les informations
        info_y = y + h + 20
        cv2.putText(frame, f"EAR: {smoothed_ear:.3f}", (x, info_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.putText(frame, f"Compteur: {self.eye_counter}/{CONFIG['EYE_AR_CONSEC_FRAMES']}",
                    (x, info_y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)

        # Afficher l'état de calibration
        if not self.calibrated:
            cv2.putText(frame, f"Calibration: {self.calibration_frames}/30",
                        (x, info_y + 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 100), 1)

        return results


# ============================================
# FONCTIONS UTILITAIRES
# ============================================

def init_camera():
    """Initialiser la caméra"""
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                print(f"📷 Caméra trouvée à l'index {i}")
                break

    if not cap.isOpened():
        print("❌ Aucune caméra détectée")
        print("Vérifiez la connexion de votre webcam")
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG['FRAME_WIDTH'])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG['FRAME_HEIGHT'])

    # Vérifier les paramètres
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"📏 Résolution: {actual_width}x{actual_height}")

    return cap


def init_audio():
    """Initialiser l'audio"""
    pygame.mixer.init()

    try:
        if os.path.exists(CONFIG['ALARM_SOUND_PATH']):
            sound = pygame.mixer.Sound(CONFIG['ALARM_SOUND_PATH'])
            print(f"🔊 Son d'alarme chargé")
        else:
            print("🔊 Création d'un bip par défaut")
            sound = create_beep_sound()
    except:
        print("🔊 Création d'un bip par défaut")
        sound = create_beep_sound()

    sound.set_volume(0.7)
    return sound


def create_beep_sound():
    """Créer un bip"""
    sample_rate = 22050
    duration = 0.3

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = 0.7 * np.sin(2 * np.pi * 800 * t)

    # Enveloppe
    envelope = np.ones_like(wave)
    attack = int(0.05 * sample_rate)
    release = int(0.1 * sample_rate)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)

    wave = wave * envelope
    wave = np.int16(wave * 32767)
    wave = np.repeat(wave.reshape(-1, 1), 2, axis=1)

    return pygame.mixer.Sound(buffer=wave.tobytes())


class DataLogger:
    def __init__(self):
        if CONFIG['LOG_DATA']:
            self.filename = f"drowsiness_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(self.filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'EAR', 'EyeState', 'EyesDetected', 'Drowsy', 'Blinks'])
            print(f"📝 Log: {self.filename}")

    def log(self, ear, eye_state, eyes_detected, drowsy, blinks):
        if CONFIG['LOG_DATA']:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, f"{ear:.3f}", eye_state, eyes_detected, drowsy, blinks])


def draw_advanced_ui(frame, fps, status, results, alarm_active):
    """Interface avancée"""
    height, width = frame.shape[:2]

    # Panneau supérieur
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, 140), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Titre
    cv2.putText(frame, "DETECTION DE SOMMOLENCE", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Statut
    y = 60
    status_color = (0, 255, 0)  # Vert par défaut

    if "SOMMOLENCE" in status:
        status_color = (0, 0, 255)  # Rouge pour somnolence
    elif "FERME" in status:
        status_color = (0, 165, 255)  # Orange pour yeux fermés

    cv2.putText(frame, f"Statut: {status}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

    # Métriques
    y += 25
    ear_color = (0, 255, 0) if results['ear'] > CONFIG['EYE_AR_THRESHOLD'] else (0, 0, 255)
    cv2.putText(frame, f"EAR: {results['ear']:.3f}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, ear_color, 1)

    # Barre de progression EAR
    bar_x, bar_y = 100, y - 8
    bar_width, bar_height = 150, 10
    ear_percent = min(1.0, results['ear'] / 0.4)

    cv2.rectangle(frame, (bar_x, bar_y),
                  (bar_x + bar_width, bar_y + bar_height),
                  (100, 100, 100), -1)
    cv2.rectangle(frame, (bar_x, bar_y),
                  (bar_x + int(bar_width * ear_percent), bar_y + bar_height),
                  ear_color, -1)

    # Seuil EAR
    threshold_x = bar_x + int((CONFIG['EYE_AR_THRESHOLD'] / 0.4) * bar_width)
    cv2.line(frame, (threshold_x, bar_y),
             (threshold_x, bar_y + bar_height),
             (255, 255, 255), 2)

    y += 25
    cv2.putText(frame, f"Yeux détectés: {results['eyes_detected']}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    y += 20
    cv2.putText(frame, f"Clignements: {results['blink_count']}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # FPS
    if CONFIG['SHOW_FPS']:
        fps_color = (0, 255, 0) if fps > 20 else (0, 165, 255) if fps > 10 else (0, 0, 255)
        cv2.putText(frame, f"FPS: {fps:.1f}", (width - 100, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, fps_color, 1)

    # Alarme
    if alarm_active:
        # LED clignotante
        if int(time.time() * 3) % 2 == 0:
            cv2.circle(frame, (width - 40, 30), 12, (0, 0, 255), -1)
        cv2.putText(frame, "ALARME!", (width - 100, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Légende
    cv2.putText(frame, "Vert=ouvert | Rouge=fermé | Bleu=visage | Jaune=zone yeux",
                (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)


# ============================================
# PROGRAMME PRINCIPAL
# ============================================

def main():
    print("\n" + "=" * 60)
    print("SYSTEME DE DETECTION DE SOMMOLENCE")
    print("=" * 60)

    # Initialisation
    detector = AdvancedDrowsinessDetector()

    cap = init_camera()
    if cap is None:
        return

    alarm_sound = init_audio()
    logger = DataLogger()

    # Variables
    prev_time = time.time()
    alarm_active = False
    alarm_start_time = None
    frame_count = 0

    print("\n⚙️  Configuration:")
    print(f"   • Seuil EAR: {CONFIG['EYE_AR_THRESHOLD']}")
    print(f"   • Frames consécutives: {CONFIG['EYE_AR_CONSEC_FRAMES']}")
    print(f"   • Taille minimale visage: {CONFIG['MIN_FACE_SIZE']}px")

    print("\n🎮 Commandes:")
    print("   Q : Quitter")
    print("   R : Réinitialiser")
    print("   S : Son ON/OFF")
    print("   + : Augmenter seuil EAR")
    print("   - : Diminuer seuil EAR")
    print("   C : Info calibration")
    print("=" * 60)

    print("\n🚀 Démarrage... Gardez les yeux ouverts face à la caméra")
    print("Le système se calibre automatiquement sur 30 frames")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Erreur de lecture de la caméra")
            break

        frame_count += 1

        # FPS
        current_time = time.time()
        fps = 1.0 / (current_time - prev_time)
        prev_time = current_time

        # Miroir pour effet naturel
        frame = cv2.flip(frame, 1)

        # Détection
        results = detector.detect(frame)

        # Statut
        status = "VIGILANT"
        if not results['face_detected']:
            status = "AUCUN VISAGE"
        elif results['is_drowsy']:
            status = "⚠️ SOMMOLENCE"
        elif results['eye_state'] == 'FERME':
            status = "YEUX FERMES"
        elif results['eyes_detected'] == 0:
            status = "YEUX NON DETECTES"

        # Alarme
        if results['is_drowsy'] and detector.alarm_triggered:
            if not alarm_active and CONFIG['ENABLE_BEEP']:
                alarm_sound.play(loops=-1)
                alarm_active = True
                alarm_start_time = current_time
                print(f"\n🚨 ALARME ACTIVÉE! Yeux fermés depuis {detector.eye_counter} frames")
                print(f"   EAR: {results['ear']:.3f} (seuil: {CONFIG['EYE_AR_THRESHOLD']:.3f})")

        # Arrêt alarme
        if alarm_active:
            if (current_time - alarm_start_time >= CONFIG['ALARM_DURATION'] or
                    not results['is_drowsy']):
                alarm_sound.stop()
                alarm_active = False
                print("🔇 Alarme arrêtée")

        # Logging
        logger.log(results['ear'], results['eye_state'],
                   results['eyes_detected'], results['is_drowsy'],
                   results['blink_count'])

        # Interface
        draw_advanced_ui(frame, fps, status, results, alarm_active)

        # Affichage
        cv2.imshow('Detection de Somnolence - Q pour quitter', frame)

        # Commandes
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            alarm_sound.stop()
            alarm_active = False
            detector.eye_counter = 0
            detector.alarm_triggered = False
            detector.drowsy_start_time = None
            print("\n🔄 Système réinitialisé")
        elif key == ord('s'):
            CONFIG['ENABLE_BEEP'] = not CONFIG['ENABLE_BEEP']
            state = "ACTIVÉ" if CONFIG['ENABLE_BEEP'] else "DÉSACTIVÉ"
            print(f"\n🔊 Son {state}")
        elif key == ord('+'):
            CONFIG['EYE_AR_THRESHOLD'] = min(0.35, CONFIG['EYE_AR_THRESHOLD'] + 0.01)
            print(f"\n📈 Seuil EAR augmenté: {CONFIG['EYE_AR_THRESHOLD']:.3f}")
        elif key == ord('-'):
            CONFIG['EYE_AR_THRESHOLD'] = max(0.15, CONFIG['EYE_AR_THRESHOLD'] - 0.01)
            print(f"\n📉 Seuil EAR diminué: {CONFIG['EYE_AR_THRESHOLD']:.3f}")
        elif key == ord('c'):
            # Info calibration
            print(f"\n📊 Information système:")
            print(f"   EAR actuel: {results['ear']:.3f}")
            print(f"   État yeux: {results['eye_state']}")
            print(f"   Yeux détectés: {results['eyes_detected']}")
            print(f"   Compteur: {detector.eye_counter}/{CONFIG['EYE_AR_CONSEC_FRAMES']}")
            print(f"   Calibré: {'OUI' if detector.calibrated else 'NON'}")
            if detector.calibrated:
                print(f"   EAR référence: {detector.ear_reference:.3f}")
            else:
                print(f"   Calibration: {detector.calibration_frames}/30 frames")

    # Nettoyage
    cap.release()
    cv2.destroyAllWindows()
    alarm_sound.stop()
    pygame.mixer.quit()

    print(f"\n✅ Programme terminé")
    print(f"📊 Statistiques:")
    print(f"   Frames totales: {frame_count}")
    print(f"   Clignements détectés: {detector.blink_counter}")
    print(f"   Seuil EAR final: {CONFIG['EYE_AR_THRESHOLD']:.3f}")
    print(f"   Calibration: {'Terminée' if detector.calibrated else 'Non terminée'}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Programme interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\n👋 Au revoir !")