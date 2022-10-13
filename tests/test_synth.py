import unittest

import numpy as np
from scipy.io import wavfile
import tempfile

from partitura.utils.synth import (
    midi_pitch_to_natural_frequency,
    exp_in_exp_out,
    lin_in_lin_out,
    additive_synthesis,
    synthesize,
)

from partitura import EXAMPLE_MUSICXML, load_score

from partitura import save_wav

from tests import WAV_TESTFILES

RNG = np.random.RandomState(1984)


class TestMidiPitchToNaturalFrequency(unittest.TestCase):
    def test_octaves(self):
        # all As
        midi_pitch = 12 * np.arange(10) + 9
        # frequencies
        frequency = midi_pitch_to_natural_frequency(midi_pitch)
        # ratio of frequencies all of them should be 2
        freq_ratios = frequency[1:] / frequency[:-1]
        # make test
        self.assertTrue(np.allclose(freq_ratios, 2))


class TestEnvelopes(unittest.TestCase):
    def test_exp_in_exp_out(self):

        num_frames = 700
        envelope = exp_in_exp_out(num_frames)

        decay_frames = num_frames // 10
        attack_frames = num_frames // 100

        envelop_attack = envelope[:attack_frames]

        envelop_decay = envelope[-decay_frames:]

        # compute second derivative, since the function of log envelope
        # since the function is exponential and the input is linear,
        # the second derivative must be 0
        diff2_attack = np.diff(np.diff(np.log(envelop_attack)))
        diff2_decay = np.diff(np.diff(np.log(envelop_decay)))

        self.assertTrue(np.allclose(diff2_attack, 0))
        self.assertTrue(np.allclose(diff2_decay, 0))

    def test_lin_in_lin_out(self):

        num_frames = 700
        envelope = lin_in_lin_out(num_frames)

        decay_frames = num_frames // 10
        attack_frames = num_frames // 100

        envelop_attack = envelope[:attack_frames]

        envelop_decay = envelope[-decay_frames:]

        # compute second derivative, since the function of envelope
        # since the function is exponential and the input is linear,
        # the second derivative must be 0
        diff2_attack = np.diff(np.diff(envelop_attack))
        diff2_decay = np.diff(np.diff(envelop_decay))

        self.assertTrue(np.allclose(diff2_attack, 0))
        self.assertTrue(np.allclose(diff2_decay, 0))


class TestAdditiveSynthesis(unittest.TestCase):
    def constant_envelope(self, x):
        return 1

    def test_freqs(self):

        for freq in np.linspace(10, 1000, 10):

            rand = RNG.rand()
            y = additive_synthesis(
                freqs=np.array([freq, freq + rand * freq]),
                duration=1,
                samplerate=100,
                envelope_fun=self.constant_envelope,
            )

            num_frames = 100
            x = np.linspace(0, 1, num_frames)
            y_target = np.sin(2 * np.pi * freq * x) + np.sin(
                2 * np.pi * (freq + rand * freq) * x
            )
            y_target *= 0.5

            self.assertTrue(np.allclose(y, y_target))

    def test_size(self):

        samplerate = np.arange(1, 100, 10) * 10
        duration = np.arange(10)

        for sr in samplerate:
            for dur in duration:

                expected_length = dur * sr

                y = additive_synthesis(freqs=440, duration=dur, samplerate=sr)

                self.assertTrue(len(y) == expected_length)


class TestSynthExport(unittest.TestCase):

    score = load_score(EXAMPLE_MUSICXML)

    def test_synthesize(self):

        for fn in WAV_TESTFILES:

            sr, original_audio = wavfile.read(fn)

            target_audio = synthesize(
                note_info=self.score,
                samplerate=sr,
                envelope_fun="linear",
                tuning="equal_temperament",
                bpm=60,
            )

            # The test seems to work on MacOS, but not on Linux...
            self.assertTrue(len(target_audio) == len(original_audio))

    def test_export(self):

        for fn in WAV_TESTFILES:
            sr, original_audio = wavfile.read(fn)
            with tempfile.TemporaryFile(suffix=".mid") as filename:

                save_wav(
                    input_data=self.score,
                    out=filename,
                    samplerate=sr,
                    tuning="equal_temperament",
                    bpm=60,
                    envelope_fun="linear",
                )

                sr_rec, rec_audio = wavfile.read(filename)

                self.assertTrue(sr_rec == sr)
                self.assertTrue(len(rec_audio) == len(original_audio))

                self.assertTrue(
                    np.allclose(
                        rec_audio / rec_audio.max(),
                        original_audio / original_audio.max(),
                        atol=1e-4,
                    )
                )

    def test_errors(self):

        # wrong envelope
        try:
            audio_signal = synthesize(
                note_info=self.score,
                samplerate=8000,
                envelope_fun="wrong keyword",
                tuning="equal_temperament",
                bpm=60,
            )
            # This test should fail
            self.assertTrue(False)
        except ValueError:
            self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
