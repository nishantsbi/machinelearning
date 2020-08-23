import tensorflow as tf

class Encoder(tf.keras.Model):
    def __init__(self, vocab_size, embedding_dim, enc_units, batch_sz, max_ques_length, embedding_matrix):
        super(Encoder, self).__init__()
        self.batch_sz = batch_sz
        self.enc_units = enc_units
        
        self.embedding = tf.keras.layers.Embedding(vocab_size, embedding_dim, 
                                                   input_length=max_ques_length, 
                                                   weights=[embedding_matrix], 
                                                   trainable=False, mask_zero=True)
        self.lstm = tf.keras.layers.LSTM(self.enc_units,
                                   return_sequences=True,
                                   return_state=True)
        
    def call(self, inputs, hidden):
        # inputs shape == (batch_size, max_ques_length)
        x = self.embedding(inputs)
        # x shape == (batch_size, max_ques_length, embedding_dim)
        mask = self.embedding.compute_mask(inputs)
        # mask shape == (batch_size, max_ques_length)
        output, state_h, state_c = self.lstm(x, initial_state=hidden, mask=mask)
        # output shape == (batch_size, max_ques_length, enc_units)
        # state_h shape == (batch_size, enc_units)
        # state_c shape == (batch_size, enc_units)
        return output, state_h, state_c

    def initialize_hidden_state(self):
        return (tf.zeros((self.batch_sz, self.enc_units)),
                tf.zeros((self.batch_sz, self.enc_units)))

class Decoder(tf.keras.Model):
    def __init__(self, vocab_size, embedding_dim, dec_units, batch_sz, max_ques_length, embedding_matrix):
        super(Decoder, self).__init__()
        self.batch_sz = batch_sz
        self.dec_units = dec_units
        self.embedding = tf.keras.layers.Embedding(vocab_size, embedding_dim, 
                                                   input_length=max_ans_length, 
                                                   weights=[embedding_matrix], 
                                                   trainable=False, mask_zero=True)
        
        self.lstm = tf.keras.layers.LSTM(self.dec_units,
                                   return_sequences=True,
                                   return_state=True)
        self.fc = tf.keras.layers.Dense(vocab_size)
        self.attention = tf.keras.layers.AdditiveAttention()

        self.masking_hidden = tf.keras.layers.Masking()
        self.masking_enc_output = tf.keras.layers.Masking()
        
    def call(self, inputs, hidden, enc_output):
        # inputs shape == (batch_size, 1)
        # hidden shape == tuple of two (batch_size, enc_units)
        # enc_output shape == (batch_size, max_ques_length, enc_units)

        hidden_with_time_axis = tf.expand_dims(hidden[0], 1)
        # hidden_with_time_axis shape == (batch_size, 1, enc_units)
        
        hidden_with_time_axis_mask = self.masking_hidden(hidden_with_time_axis)
        # hidden_with_time_axis_mask._keras_mask shape == (batch_size, 1)
        
        enc_output_mask = self.masking_enc_output(enc_output)
        # enc_output_mask._keras_mask shape == (batch_size, max_ques_length)
        
        context_vector = self.attention(inputs=[hidden_with_time_axis, enc_output],
                                        mask=[hidden_with_time_axis_mask._keras_mask, enc_output_mask._keras_mask])
        # context_vector shape == (batch_size, 1, enc_units)

        
        # x shape after passing through embedding == (batch_size, 1, embedding_dim)
        x = self.embedding(inputs)

        mask = self.embedding.compute_mask(inputs)
        # mask shape == (batch_size, 1)

        # x shape after concatenation == (batch_size, 1, embedding_dim + hidden_size)
        x = tf.concat([context_vector, x], axis=-1)
        
        # passing the concatenated vector to the LSTM
        output, state_h, state_c = self.lstm(x, initial_state=hidden, mask=mask)
        # output shape == (batch_size, 1, dec_units)
        # state_h shape == (batch_size, dec_units)
        # state_c shape == (batch_size, dec_units)
 
        output = tf.reshape(output, (-1, output.shape[2]))
        # output shape == (batch_size * 1, dec_units)
        
        x = self.fc(output)
        # output shape == (batch_size, vocab)
        
        return x, state_h, state_c

    def initialize_hidden_state(self):
        return (tf.zeros((self.batch_sz, self.dec_units)),
                tf.zeros((self.batch_sz, self.dec_units)))