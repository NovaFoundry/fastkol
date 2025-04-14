package rabbitmq

import (
	"context"
	"encoding/json"

	amqp "github.com/rabbitmq/amqp091-go"
)

type Client struct {
	conn    *amqp.Connection
	channel *amqp.Channel
}

func NewClient(url string) (*Client, error) {
	conn, err := amqp.Dial(url)
	if err != nil {
		return nil, err
	}

	ch, err := conn.Channel()
	if err != nil {
		conn.Close()
		return nil, err
	}

	// 声明队列
	_, err = ch.QueueDeclare(
		"crawler_tasks", // 队列名
		true,            // 持久化
		false,           // 自动删除
		false,           // 排他性
		false,           // 不等待
		nil,             // 参数
	)
	if err != nil {
		ch.Close()
		conn.Close()
		return nil, err
	}

	return &Client{
		conn:    conn,
		channel: ch,
	}, nil
}

func (c *Client) PublishTask(ctx context.Context, task interface{}) error {
	body, err := json.Marshal(task)
	if err != nil {
		return err
	}

	return c.channel.PublishWithContext(
		ctx,
		"",              // 交换机
		"crawler_tasks", // 路由键
		false,           // 强制
		false,           // 立即
		amqp.Publishing{
			DeliveryMode: amqp.Persistent,
			ContentType:  "application/json",
			Body:         body,
		},
	)
}

func (c *Client) Close() error {
	if err := c.channel.Close(); err != nil {
		return err
	}
	return c.conn.Close()
}
